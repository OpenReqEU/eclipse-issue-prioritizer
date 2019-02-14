import connexion
import logging
from application.models.prioritized_recommendations_request import PrioritizedRecommendationsRequest  # noqa: E501
from application.models.prioritized_recommendations_response import PrioritizedRecommendationsResponse  # noqa: E501
from application.models.delete_profile_response import DeleteProfileResponse  # noqa: E501
from application.models.like_requirement_request import LikeRequirementRequest  # noqa: E501
from application.models.like_requirement_response import LikeRequirementResponse  # noqa: E501
from application.models.defer_requirement_request import DeferRequirementRequest  # noqa: E501
from application.models.defer_requirement_response import DeferRequirementResponse  # noqa: E501
from application.models.delete_profile_request import DeleteProfileRequest  # noqa: E501
from application.models.chart_response import ChartResponse  # noqa: E501
from application.models.requirement import Requirement  # noqa: E501
from application.services import requirementprioritizer
from application.services import bugzillafetcher
from application.util import helper
from typing import List  # noqa: F401
from datetime import datetime, timedelta
from flask import current_app as app
from flask import json
from cachetools import TTLCache
from scipy.stats import bernoulli
import random
import string
import pickledb
import urllib
import os


db = pickledb.load(os.path.join(helper.DATA_PATH, "storage.db"), False)
_logger = logging.getLogger(__name__)
FILTER_CHARACTERS_AT_BEGINNING_OR_END = ['.', ',', '(', ')', '[', ']', '|', ':', ';']
CACHED_PRIORITIZATIONS = TTLCache(maxsize=8388608, ttl=60*60*3)  # caching for 3 hours
CACHED_CHART_URLs = TTLCache(maxsize=1048576, ttl=60*60*3)  # caching for 3 hours
CHART_REQUESTs = TTLCache(maxsize=8388608, ttl=60*60*3)  # caching for 3 hours
ASSIGNED_RESOLVED_REQUIREMENTS_OF_STAKEHOLDER = {}


def generate_chart_url(body):  #noga: E501
    response = None

    if connexion.request.is_json:
        content = connexion.request.get_json()
        app.logger.info("Generate Chart: {}".format(content))
        request = PrioritizedRecommendationsRequest.from_dict(content)

        if request.unique_key() in CACHED_CHART_URLs:
            chart_url = CACHED_CHART_URLs[request.unique_key()]
            chart_key = chart_url.split("/")[-1]
            if chart_key in CHART_REQUESTs:
                return ChartResponse(False, None, CACHED_CHART_URLs[request.unique_key()])

        chart_key = "".join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(16))
        chart_url = "http://{}:{}/prioritizer/chart/c/{}".format(helper.app_host(), helper.app_port(), chart_key)

        limit_bugs = 0  #800
        bugzilla_fetcher = bugzillafetcher.BugzillaFetcher("https://bugs.eclipse.org/bugs/rest/bug")
        bugs = bugzilla_fetcher.fetch_bugs(request.assignee, request.products, request.components,
                                           "RESOLVED", limit=limit_bugs)
        requirements = list(map(lambda b: Requirement.from_bug(b), bugs))
        ASSIGNED_RESOLVED_REQUIREMENTS_OF_STAKEHOLDER[request.unique_key()] = requirements
        CACHED_CHART_URLs[request.unique_key()] = chart_url
        CHART_REQUESTs[chart_key] = request
        response = ChartResponse(False, None, chart_url)

    return response


def recommend_prioritized_issues(body):  # noqa: E501
    """Retrieve an ordered list of recommended requirements.

     # noqa: E501

    :param body: Requirement objects for which the social popularity should be measured
    :type body: list | bytes

    :rtype: List[Requirement]
    """

    response = None
    prioritizer = requirementprioritizer.RequirementPrioritizer(db)

    if connexion.request.is_json:
        content = connexion.request.get_json()
        request = PrioritizedRecommendationsRequest.from_dict(content)
        limit = 75
        max_age_years = 7  # TODO: outsource this!!!
        refetch_threshold_limit = limit - 5
        reserved_aids = {
            'a1a1a1a1a': 0,
            'b2b2b2b2b': 1
        }

        version_key = "VERSION_{}".format(request.agent_id)
        version = db.get(version_key) if request.agent_id not in reserved_aids else reserved_aids[request.agent_id]

        if version is False:
            version = bernoulli.rvs(0.5)
            db.set(version_key, version)
            db.dump()

        fetch = True
        is_version_redirect = False

        if request.unique_key() in CACHED_PRIORITIZATIONS:
            requirements, user_profile, _ = CACHED_PRIORITIZATIONS[request.unique_key()]
            sorted_requirements, is_version_redirect = prioritizer.prioritize(
                agent_id=request.agent_id, requirements=requirements,
                user_profile=user_profile, preferred_keywords=request.keywords,
                max_age_years=max_age_years, version=version)
            fetch = len(sorted_requirements) < refetch_threshold_limit

        if fetch:
            try:
                result = prioritizer.fetch_and_prioritize(agent_id=request.agent_id, assignee=request.assignee,
                                                          components=request.components, products=request.products,
                                                          preferred_keywords=request.keywords, limit=limit,
                                                          max_age_years=max_age_years, version=version)
                sorted_requirements, user_profile, is_version_redirect = result
                CACHED_PRIORITIZATIONS[request.unique_key()] = result
            except:
                return PrioritizedRecommendationsResponse(True, "An error occurred! Please try again later.")

        ranked_bugs_list = []
        app.logger.info("Prioritize: version={}; version_redirect={}; request=({})".format(version, is_version_redirect,
                                                                                           content))

        for r in sorted_requirements:
            ranked_bugs_list += [{
                "id": r.id,
                "summary": r.summary,
                "product": r.product,
                "component": r.component,
                "priority":  int("{0:.0f}".format(r.computed_priority)),
                "numberOfCC": len(r.cc),
                "milestone": r.target_milestone,
                "keywords": r.summary_tokens,
                "creation_time": r.creation_time,
                "liked": db.exists("LIKE_{}_{}".format(request.agent_id, r.id)),
                "url": "/prioritizer/view/i/{}/k/{}".format(r.id, urllib.parse.quote(request.unique_key(), safe=''))
            }]

        response = PrioritizedRecommendationsResponse(False, None, ranked_bugs=ranked_bugs_list)

    return response


def like_prioritized_issue(body):  # noqa: E501
    response = None

    if connexion.request.is_json:
        content = connexion.request.get_json()
        request = LikeRequirementRequest.from_dict(content)
        version = db.get("VERSION_{}".format(request.agent_id))
        ranked_position, priority = rank_position_of_issue(request.id, request.agent_id, request.assignee,
                                                           request.components, request.products, request.keywords)
        app.logger.info("Like: version={}; ranked_position={}; priority={}; request=({})"
                        .format(version, ranked_position, priority, content))
        response = LikeRequirementResponse(False, None)
        db.set("LIKE_{}_{}".format(request.agent_id, request.id), request.unique_key())
        db.dump()

    return response


def rank_position_of_issue(requirement_id: int, agent_id: str, assignee: str, components: List[str],
                           products: List[str], keywords: List[str]):
    unique_key = PrioritizedRecommendationsRequest(agent_id=agent_id, assignee=assignee, components=components,
                                                   products=products, keywords=keywords).unique_key()

    if unique_key not in CACHED_PRIORITIZATIONS:
        return None, None

    sorted_requirements, _, _ = CACHED_PRIORITIZATIONS[unique_key]
    filtered_issues = list(filter(lambda r: r.id == requirement_id, sorted_requirements))
    if len(filtered_issues) != 1:
        return None, None

    ranked_position = list(map(lambda r: r.id, sorted_requirements)).index(requirement_id)
    return ranked_position, filtered_issues[0].computed_priority


def unlike_prioritized_issue(body):  # noqa: E501
    response = None

    if connexion.request.is_json:
        content = connexion.request.get_json()
        request = LikeRequirementRequest.from_dict(content)
        version = db.get("VERSION_{}".format(request.agent_id))
        ranked_position, priority = rank_position_of_issue(request.id, request.agent_id, request.assignee,
                                                           request.components, request.products, request.keywords)
        app.logger.info("Unlike: version={}; ranked_position={}; priority={}; request=({})"
                        .format(version, ranked_position, priority, content))
        response = LikeRequirementResponse(False, None)
        key = "LIKE_{}_{}".format(request.agent_id, request.id)
        if db.exists(key):
            db.rem(key)
            db.dump()

    return response


def dislike_prioritized_issue(body):  # noqa: E501
    response = None

    if connexion.request.is_json:
        content = connexion.request.get_json()
        request = LikeRequirementRequest.from_dict(content)
        version = db.get("VERSION_{}".format(request.agent_id))
        ranked_position, priority = rank_position_of_issue(request.id, request.agent_id, request.assignee,
                                                           request.components, request.products, request.keywords)
        app.logger.info("Dislike: version={}; ranked_position={}; priority={}; request=({})"
                        .format(version, ranked_position, priority, content))
        response = LikeRequirementResponse(False, None)
        db.set("DISLIKE_{}_{}".format(request.agent_id, request.id), request.unique_key())
        db.dump()

    return response


def defer_prioritized_issue(body):  # noqa: E501
    response = None

    if connexion.request.is_json:
        content = connexion.request.get_json()
        request = DeferRequirementRequest.from_dict(content)
        version = db.get("VERSION_{}".format(request.agent_id))
        ranked_position, priority = rank_position_of_issue(request.id, request.agent_id, request.assignee,
                                                           request.components, request.products, request.keywords)
        app.logger.info("Defer: version={}; ranked_position={}; priority={}; request=({})"
                        .format(version, ranked_position, priority, content))
        response = DeferRequirementResponse(False, None)
        expiration_date = datetime.now() + timedelta(days=request.interval)
        expiration_date = json.dumps(str(expiration_date))
        db.set("DEFER_{}_{}".format(request.agent_id, request.id),
               (request.unique_key(), request.interval, expiration_date))
        db.dump()

    return response


def delete_profile(body):  # noqa: E501
    response = None

    if connexion.request.is_json:
        content = connexion.request.get_json()
        request = DeleteProfileRequest.from_dict(content)
        version = db.get("VERSION_{}".format(request.agent_id))
        app.logger.info("Delete profile: version={}; request=({})".format(version, content))
        all_keys = db.getall()
        keys_to_be_removed = list(filter(lambda k: request.agent_id in k, all_keys))
        for key in keys_to_be_removed:
            db.rem(key)
        db.dump()
        response = DeleteProfileResponse(False, None)

    return response

