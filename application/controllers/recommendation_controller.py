import connexion
import logging
from application.models.request import Request  # noqa: E501
from application.models.response import Response  # noqa: E501
from application.models.response_chart import ResponseChart  # noqa: E501
from application.models.requirement import Requirement  # noqa: E501
from application.services import bugzillafetcher
from application.services import keywordextractor
from application.util import helper
from typing import List  # noqa: F401
import random
import string


_logger = logging.getLogger(__name__)
FILTER_CHARACTERS_AT_BEGINNING_OR_END = ['.', ',', '(', ')', '[', ']', '|', ':', ';']
CACHED_RESPONSE = {}
CHART_URLs = {}
CHART_REQUESTs = {}
ASSIGNED_RESOLVED_REQUIREMENTS_OF_STAKEHOLDER = {}
ASSIGNED_NEW_REQUIREMENTS_OF_STAKEHOLDER = {}


def generate_chart_url(body):  #noga: E501
    response = None

    if connexion.request.is_json:
        content = connexion.request.get_json()
        request = Request.from_dict(content)
        if request.unique_key() in CHART_URLs:
            return ResponseChart(False, None, CHART_URLs[request.unique_key()])

        #chart_key = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        chart_key = "".join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(16))
        chart_url = "http://{}:{}/prioritizer/chart/c/{}".format(helper.app_host(), helper.app_port(), chart_key)

        if request.unique_key() not in ASSIGNED_RESOLVED_REQUIREMENTS_OF_STAKEHOLDER:
            limit_bugs = 800
            bugzilla_fetcher = bugzillafetcher.BugzillaFetcher("https://bugs.eclipse.org/bugs/rest/bug")
            bugs = bugzilla_fetcher.fetch_bugs(request.assignee, request.products, request.components, "RESOLVED", limit=limit_bugs)
            requirements = list(map(lambda b: Requirement.from_bug(b), bugs))
            ASSIGNED_RESOLVED_REQUIREMENTS_OF_STAKEHOLDER[request.unique_key()] = requirements

            new_bugs = bugzilla_fetcher.fetch_bugs(request.assignee, request.products, request.components, "NEW", limit=limit_bugs)
            new_requirements = list(map(lambda b: Requirement.from_bug(b), new_bugs))
            ASSIGNED_NEW_REQUIREMENTS_OF_STAKEHOLDER[request.unique_key()] = new_requirements

        CHART_URLs[request.unique_key()] = chart_url
        CHART_REQUESTs[chart_key] = request
        response = ResponseChart(False, None, chart_url)

    return response


def recommend_prioritized_issues(body):  # noqa: E501
    """Retrieve an ordered list of recommended requirements.

     # noqa: E501

    :param body: Requirement objects for which the social popularity should be measured
    :type body: list | bytes

    :rtype: List[Requirement]
    """

    response = None

    if connexion.request.is_json:
        content = connexion.request.get_json()
        request = Request.from_dict(content)

        if request.unique_key() in CACHED_RESPONSE:
            return CACHED_RESPONSE[request.unique_key()]

        # compute user profile (based on keywords)
        limit_bugs = 800
        # TODO: error handling!!
        bugzilla_fetcher = bugzillafetcher.BugzillaFetcher("https://bugs.eclipse.org/bugs/rest/bug")
        bugs = bugzilla_fetcher.fetch_bugs(request.assignee, request.products, request.components,
                                           "RESOLVED", limit=limit_bugs)
        requirements = list(map(lambda b: Requirement.from_bug(b), bugs))
        keyword_extractor = keywordextractor.KeywordExtractor()
        user_extracted_keywords = keyword_extractor.extract_keywords(requirements, enable_pos_tagging=False,
                                                                     enable_lemmatization=False, lang="en")

        # advanced content-based recommendation with MAUT
        limit_bugs = 75
        new_bugs = bugzilla_fetcher.fetch_bugs(None, request.products, request.components, "NEW", limit=limit_bugs)
        new_requirements = list(map(lambda b: Requirement.from_bug(b), new_bugs))
        keyword_extractor.extract_keywords(new_requirements, enable_pos_tagging=False, enable_lemmatization=False, lang="en")

        bug_comments = bugzilla_fetcher.async_fetch_comments(list(map(lambda r: r.id, new_requirements)))

        for r in new_requirements:
            comments = bug_comments[r.id]
            r.number_of_comments = len(comments)

        version = 0
        total_sum_of_priorities = 0.0
        preferred_keywords = request.keywords
        for r in new_requirements:
            if version == 0:
                r.computed_priority = compute_contentbased_maut_priority(request.assignee, user_extracted_keywords, preferred_keywords, r)
            elif version == 1:
                r.computed_priority = compute_contentbased_priority(user_extracted_keywords, preferred_keywords, r)
            #else:
            #    r.computed_priority = compute_collaborative_priority(request.assignee, user_extracted_keywords, preferred_keywords, r)
            total_sum_of_priorities += r.computed_priority

        for r in new_requirements:
            r.computed_priority *= 100.0 / total_sum_of_priorities

        new_requirements = filter(lambda r: r.computed_priority > 0.0, new_requirements)
        sorted_requirements = sorted(new_requirements, key=lambda r: r.computed_priority, reverse=True)

        ranked_bugs_list = []
        for r in sorted_requirements:
            ranked_bugs_list += [{
                "id": r.id,
                "summary": r.summary,
                "product": r.product,
                "component": r.component,
                "priority": float("{0:.2f}".format(r.computed_priority)),
                "numberOfCC": len(r.cc),
                "milestone": r.target_milestone,
                "keywords": r.summary_tokens
            }]

        response = Response(False, None, rankedBugs=ranked_bugs_list)
        CACHED_RESPONSE[request.unique_key()] = response

    return response


def _keyword_weight(k, preferred_keywords):
    # TODO: does not work!!
    weight_of_preferred_keyword = 3.0
    return weight_of_preferred_keyword if k in preferred_keywords else 1.0


def compute_contentbased_priority(keywords_of_stakeholder: List[str], preferred_keywords: List[str], requirement: Requirement) -> float:
    #keyword_occurrences = dict(map(lambda k: (k, requirement.summary_tokens.count(k) * _keyword_weight(k, preferred_keywords)), keywords_of_stakeholder))
    #keyword_occurrences_of_existing_keywords = dict(map(lambda k: (k, requirement.summary_tokens.count(k) * _keyword_weight(k, preferred_keywords)), filter(lambda k: k in requirement.summary_tokens, keywords_of_stakeholder)))
    keyword_occurrences = dict(map(lambda k: (k, int(k in requirement.summary_tokens) * _keyword_weight(k, preferred_keywords)), keywords_of_stakeholder))
    keyword_occurrences_of_existing_keywords = dict(map(lambda k: (k, int(k in requirement.summary_tokens) * _keyword_weight(k, preferred_keywords)), filter(lambda k: k in requirement.summary_tokens, keywords_of_stakeholder)))
    assert(sum(keyword_occurrences_of_existing_keywords.values()) == sum(keyword_occurrences.values()))
    n_keyword_occurrences = sum(keyword_occurrences.values())
    n_keywords_of_stakeholder = len(keywords_of_stakeholder)
    return float(n_keyword_occurrences) / float(n_keywords_of_stakeholder) if n_keywords_of_stakeholder > 0 else 0.0


def compute_contentbased_maut_priority(assignee_email_address: str, keywords_of_stakeholder: List[str],
                                       preferred_keywords: List[str], requirement: Requirement) -> float:
    """
        Assigned to me:    2.5
        Gerrit Changes:    2.2
        Comments:          1.9
        CC:                1.7
        Blocker:           1.4
    """
    #keyword_occurrences = dict(map(lambda k: (k, requirement.summary_tokens.count(k) * _keyword_weight(k, preferred_keywords)), keywords_of_stakeholder))
    #keyword_occurrences_of_existing_keywords = dict(map(lambda k: (k, requirement.summary_tokens.count(k) * _keyword_weight(k, preferred_keywords)), filter(lambda k: k in requirement.summary_tokens, keywords_of_stakeholder)))
    keyword_occurrences = dict(map(lambda k: (k, int(k in requirement.summary_tokens) * _keyword_weight(k, preferred_keywords)), keywords_of_stakeholder))
    keyword_occurrences_of_existing_keywords = dict(map(lambda k: (k, int(k in requirement.summary_tokens) * _keyword_weight(k, preferred_keywords)), filter(lambda k: k in requirement.summary_tokens, keywords_of_stakeholder)))
    assert(sum(keyword_occurrences_of_existing_keywords.values()) == sum(keyword_occurrences.values()))
    print("-"*80)
    print(requirement.id)
    print(keyword_occurrences_of_existing_keywords)
    print("-"*80)
    n_keyword_occurrences = sum(keyword_occurrences.values())
    n_keywords_of_stakeholder = len(keywords_of_stakeholder)
    responsibility_weight = max(float(n_keyword_occurrences) / float(n_keywords_of_stakeholder) if n_keywords_of_stakeholder > 0 else 0.0, 0.05)
    is_assigned_to_me = requirement.assigned_to == assignee_email_address
    n_assigned_to_me = 1.0 if is_assigned_to_me else 0.0
    n_cc_recipients = len(requirement.cc)
    n_blocks = len(requirement.blocks)
    n_gerrit_changes = len(requirement.see_also) # TODO: filter only "https://git.eclipse.org/..." URLs
    n_comments = requirement.number_of_comments

    # TODO: this must be normalized (calculate the mean and take the difference to the mean value into account)
    sum_of_dimension_contributions = n_assigned_to_me * 2.5 + n_cc_recipients * 1.7 \
                                   + n_gerrit_changes * 2.2 + n_blocks * 1.4 + n_comments * 1.9
    return sum_of_dimension_contributions * responsibility_weight


def perform_prioritization():
    # compute user profile (based on keywords)
    limit_bugs = 400
    bugzilla_fetcher = bugzillafetcher.BugzillaFetcher("https://bugs.eclipse.org/bugs/rest/bug")

    bugs = bugzilla_fetcher.fetch_bugs(None, [], [], None, limit=10000)
    requirements = list(map(lambda b: Requirement.from_bug(b), bugs))
    keyword_extractor = keywordextractor.KeywordExtractor()
    keyword_extractor.extract_keywords(requirements, enable_pos_tagging=False, enable_lemmatization=False, lang="en")
    for r in requirements:
        print(r.summary_tokens)
    import sys;sys.exit()

    bugs = bugzilla_fetcher.fetch_bugs("lars.vogel@vogella.com", ["Platform"], ["UI", "test"], "RESOLVED", limit=limit_bugs)
    requirements = list(map(lambda b: Requirement.from_bug(b), bugs))
    print(len(requirements))
    keyword_extractor = keywordextractor.KeywordExtractor()
    user_extracted_keywords = keyword_extractor.extract_keywords(requirements, enable_pos_tagging=False,
                                                                 enable_lemmatization=False, lang="en")
    print(user_extracted_keywords)
    print("Number of extracted keywords: {}".format(len(user_extracted_keywords)))

    # advanced content-based recommendation with MAUT
    new_bugs = bugzilla_fetcher.fetch_bugs("lars.vogel@vogella.com", ["Platform"], ["UI", "test"], "NEW", limit=limit_bugs)
    new_requirements = list(map(lambda b: Requirement.from_bug(b), new_bugs))
    print(len(new_requirements))
    keyword_extractor.extract_keywords(new_requirements, enable_pos_tagging=False, enable_lemmatization=False, lang="en")

    total_sum_of_maut_priorities = 0.0
    for r in new_requirements:
        comments = bugzilla_fetcher.fetch_comments(r.id)
        print("Requirement {}: number of comments for requirement: {}".format(r.id, len(comments)))
        r.number_of_comments = len(comments)
        r.computed_priority = compute_contentbased_maut_priority("lars.vogel@vogella.com", user_extracted_keywords, r)
        total_sum_of_maut_priorities += r.computed_priority

    for r in new_requirements:
        r.computed_priority *= 100.0 / total_sum_of_maut_priorities

    sorted_requirements = sorted(new_requirements, key=lambda r: r.computed_priority, reverse=True)
    for r in sorted_requirements:
        print("{}: {}".format(r.summary[:20], r.computed_priority))

