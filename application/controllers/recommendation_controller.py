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
import random
import string
import pickledb
import os
from flask import json
from cachetools import TTLCache


db = pickledb.load(os.path.join(helper.DATA_PATH, "storage.db"), False)
_logger = logging.getLogger(__name__)
FILTER_CHARACTERS_AT_BEGINNING_OR_END = ['.', ',', '(', ')', '[', ']', '|', ':', ';']
CACHED_PRIORITIZATIONS = TTLCache(maxsize=8388608, ttl=60*60*3)  # caching for 3 hours
CACHED_CHART_URLs = TTLCache(maxsize=1048576, ttl=60*60*3)  # caching for 3 hours
CHART_REQUESTs = TTLCache(maxsize=8388608, ttl=60*60*3)  # caching for 3 hours
ASSIGNED_RESOLVED_REQUIREMENTS_OF_STAKEHOLDER = {}
ASSIGNED_NEW_REQUIREMENTS_OF_STAKEHOLDER = {}


def generate_chart_url(body):  #noga: E501
    response = None

    if connexion.request.is_json:
        content = connexion.request.get_json()
        request = PrioritizedRecommendationsRequest.from_dict(content)

        if request.unique_key() in CACHED_CHART_URLs:
            chart_url = CACHED_CHART_URLs[request.unique_key()]
            chart_key = chart_url.split("/")[-1]
            if chart_key in CHART_REQUESTs:
                return ChartResponse(False, None, CACHED_CHART_URLs[request.unique_key()])

        chart_key = "".join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(16))
        chart_url = "http://{}:{}/prioritizer/chart/c/{}".format(helper.app_host(), helper.app_port(), chart_key)

        limit_bugs = 800
        bugzilla_fetcher = bugzillafetcher.BugzillaFetcher("https://bugs.eclipse.org/bugs/rest/bug")
        bugs = bugzilla_fetcher.fetch_bugs(request.assignee, request.products, request.components, "RESOLVED", limit=limit_bugs)
        requirements = list(map(lambda b: Requirement.from_bug(b), bugs))
        ASSIGNED_RESOLVED_REQUIREMENTS_OF_STAKEHOLDER[request.unique_key()] = requirements

        new_bugs = bugzilla_fetcher.fetch_bugs(request.assignee, request.products, request.components, "NEW", limit=limit_bugs)
        new_requirements = list(map(lambda b: Requirement.from_bug(b), new_bugs))
        ASSIGNED_NEW_REQUIREMENTS_OF_STAKEHOLDER[request.unique_key()] = new_requirements

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

        if request.unique_key() in CACHED_PRIORITIZATIONS:
            return CACHED_PRIORITIZATIONS[request.unique_key()]

        # TODO: error handling!!
        sorted_requirements = prioritizer.prioritize(agent_id=request.agent_id, assignee=request.assignee,
                                                     components=request.components, products=request.products,
                                                     preferred_keywords=request.keywords)

        ranked_bugs_list = []
        for r in sorted_requirements:
            ranked_bugs_list += [{
                "id": r.id,
                "summary": r.summary,
                "product": r.product,
                "component": r.component,
                "priority":  float("{0:.2f}".format(r.computed_priority)),
                "numberOfCC": len(r.cc),
                "milestone": r.target_milestone,
                "keywords": r.summary_tokens
            }]

        response = PrioritizedRecommendationsResponse(False, None, rankedBugs=ranked_bugs_list)
        CACHED_PRIORITIZATIONS[request.unique_key()] = response

    return response


def like_prioritized_issue(body):  # noqa: E501
    response = None

    if connexion.request.is_json:
        content = connexion.request.get_json()
        request = LikeRequirementRequest.from_dict(content)
        response = LikeRequirementResponse(False, None)
        db.set("LIKE_{}_{}".format(request.agent_id, request.id), request.unique_key())
        db.dump()

    return response


def dislike_prioritized_issue(body):  # noqa: E501
    response = None

    if connexion.request.is_json:
        content = connexion.request.get_json()
        request = LikeRequirementRequest.from_dict(content)
        response = LikeRequirementResponse(False, None)
        db.set("DISLIKE_{}_{}".format(request.agent_id, request.id), request.unique_key())
        db.dump()

    return response


def defer_prioritized_issue(body):  # noqa: E501
    response = None

    if connexion.request.is_json:
        content = connexion.request.get_json()
        request = DeferRequirementRequest.from_dict(content)
        response = DeferRequirementResponse(False, None)
        expiration_date = datetime.now() + timedelta(days=request.interval)
        expiration_date = json.dumps(str(expiration_date))
        db.set("DEFER_{}_{}".format(request.agent_id, request.id), (request.unique_key(), request.interval, expiration_date))
        db.dump()

    return response


def delete_profile(body):  # noqa: E501
    response = None

    if connexion.request.is_json:
        content = connexion.request.get_json()
        request = DeleteProfileRequest.from_dict(content)
        all_keys = db.getall()
        keys_to_be_removed = list(filter(lambda k: request.agent_id in k, all_keys))
        for key in keys_to_be_removed:
            db.rem(key)
        db.dump()
        response = DeleteProfileResponse(False, None)

    return response

