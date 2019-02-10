# coding: utf-8

from application.models.requirement import Requirement
import logging
from application.services import bugzillafetcher
from application.services import keywordextractor
from application.util import helper
from dateutil import parser
from flask import json
from datetime import datetime, timedelta
from typing import List  # noqa: F401
from collections import Counter
import numpy as np
import collections


_logger = logging.getLogger(__name__)
MedianResults = collections.namedtuple("MedianResults", [
    "n_cc_recipients",
    "n_blocks",
    "n_gerrit_changes",
    "n_comments",
    "max_age_years"
])


class RequirementPrioritizer(object):

    def __init__(self, db):
        self.db = db
        self.bugzilla_fetcher = bugzillafetcher.BugzillaFetcher("https://bugs.eclipse.org/bugs/rest/bug")
        self.keyword_extractor = keywordextractor.KeywordExtractor()

    def _reward_liked_requirement(self, agent_id: str, requirement: Requirement):
        like_unique_key = self.db.get("LIKE_{}_{}".format(agent_id, requirement.id))
        requirement.reward = like_unique_key is not False
        return requirement

    def _is_relevant_requirement(self, agent_id: str, requirement: Requirement) -> bool:
        defer_db_key = "DEFER_{}_{}".format(agent_id, requirement.id)
        dislike_unique_key = self.db.get("DISLIKE_{}_{}".format(agent_id, requirement.id))
        result = self.db.get(defer_db_key)
        defer_unique_key = result[0] if result is not False else None
        defer_interval = result[1] if result is not False else ""
        defer_expiration_date = parser.parse(json.loads(result[2])) if result is not False else None
        now = datetime.now()

        if dislike_unique_key is not False:
            return False

        if defer_unique_key is not False and defer_expiration_date is not None:
            if now <= defer_expiration_date:
                return False
            else:
                self.db.rem(defer_db_key)
                self.db.dump()

        return True

    def compute_user_profile(self, assignee: str, components: List[str], products: List[str],
                             limit: int=0, max_age_years: int=7) -> List[str]:
        # compute user profile (based on keywords)
        bugs = self.bugzilla_fetcher.fetch_bugs(assignee, products, components, "RESOLVED", limit=limit,
                                                max_age_years=max_age_years)
        requirements = list(map(lambda b: Requirement.from_bug(b), bugs))
        components = list(map(lambda r: r.component, requirements))
        component_frequencies = Counter(components)
        return component_frequencies, self.keyword_extractor.extract_keywords(requirements, enable_pos_tagging=False,
                                                                              enable_lemmatization=False, lang="en")

    def fetch_and_prioritize(self, agent_id: str, assignee: str, components: List[str], products: List[str],
                             preferred_keywords: List[str], limit: int, version: int) -> (List[Requirement], List[str], List[str]):
        # advanced content-based recommendation with MAUT
        max_age_years = 7
        user_component_frequencies, user_profile_keywords = self.compute_user_profile(assignee=assignee,
                                                                                      components=components,
                                                                                      products=products,
                                                                                      limit=0,
                                                                                      max_age_years=max_age_years)
        new_bugs = self.bugzilla_fetcher.fetch_bugs(None, products, components, "NEW", max_age_years=max_age_years)
        new_requirements = list(map(lambda b: Requirement.from_bug(b), new_bugs))

        # since we have to deal with a large number of issues, the number of request to fetch the issues' comments
        # must be limited -> therefore we prioritize the issues without taking the comments into account
        # and only consider the 75 top-most issues with the highest priority. Only for these issues we fetch
        # the comments and finally do the final prioritization where we also take into account the comments.
        new_requirements = self.prioritize(agent_id=agent_id, requirements=new_requirements, assignee=assignee,
                                           user_component_frequencies=user_component_frequencies,
                                           user_profile_keywords=user_profile_keywords,
                                           preferred_keywords=preferred_keywords,
                                           max_age_years=max_age_years,
                                           version=version)
        new_requirements = new_requirements[:limit]

        bug_comments = self.bugzilla_fetcher.fetch_comments_parallelly(list(map(lambda r: r.id, new_requirements)))
        for r in new_requirements:
            comments = bug_comments[r.id]
            r.number_of_comments = len(comments)

        new_requirements = self.prioritize(agent_id=agent_id, requirements=new_requirements, assignee=assignee,
                                           user_component_frequencies=user_component_frequencies,
                                           user_profile_keywords=user_profile_keywords,
                                           preferred_keywords=preferred_keywords,
                                           max_age_years=max_age_years,
                                           version=version)
        return new_requirements, user_component_frequencies, user_profile_keywords, preferred_keywords

    def prioritize(self, agent_id: str, requirements: List[Requirement], assignee: str,
                   user_component_frequencies: Counter, user_profile_keywords: List[str],
                   preferred_keywords: List[str], max_age_years: int, version: int) -> List[Requirement]:
        requirements = list(filter(lambda r: self._is_relevant_requirement(agent_id, r), requirements))
        requirements = list(map(lambda r: self._reward_liked_requirement(agent_id, r), requirements))
        self.keyword_extractor.extract_keywords(requirements, enable_pos_tagging=False,
                                                enable_lemmatization=False, lang="en")
        median_n_cc_recipients = max(np.median(list(map(lambda r: len(r.cc), requirements))), 1e-2)
        median_n_blocks = max(np.median(list(map(lambda r: len(r.blocks), requirements))), 1e-2)  # TODO: filter only "https://git.eclipse.org/..." URLs
        median_n_gerrit_changes = max(np.median(list(map(lambda r: len(r.see_also), requirements))), 1e-2)
        median_n_comments = max(np.median(list(map(lambda r: r.number_of_comments or 0.0, requirements))), 1e-2)
        median_results = MedianResults(n_cc_recipients=median_n_cc_recipients, n_blocks=median_n_blocks,
                                       n_gerrit_changes=median_n_gerrit_changes, n_comments=median_n_comments,
                                       max_age_years=max_age_years)

        max_priority = 0.0
        for r in requirements:
            if version == 0:
                r.computed_priority = compute_contentbased_maut_priority(assignee, user_component_frequencies,
                                                                         user_profile_keywords, preferred_keywords,
                                                                         median_results, r)
            elif version == 1:
                r.computed_priority = compute_contentbased_priority(user_profile_keywords, preferred_keywords, r)
            #else:
            #    r.computed_priority = compute_collaborative_priority(request.assignee, user_extracted_keywords,
            #                                                         preferred_keywords, r)
            r.computed_priority = r.computed_priority * (5 if r.reward else 1)
            if r.computed_priority > max_priority:
                max_priority = r.computed_priority

        for r in requirements:
            r.computed_priority = max(r.computed_priority * 100.0 / max_priority, 1.0) if max_priority > 0.0 else 1.0

        requirements = filter(lambda r: r.computed_priority >= 0.01, requirements)
        return sorted(requirements, key=lambda r: r.computed_priority, reverse=True)


def compute_contentbased_priority(keywords_of_stakeholder: List[str], preferred_keywords: List[str], requirement: Requirement) -> float:
    #keyword_occurrences = dict(map(lambda k: (k, requirement.summary_tokens.count(k) * _keyword_weight(k, preferred_keywords)), keywords_of_stakeholder))
    #keyword_occurrences_of_existing_keywords = dict(map(lambda k: (k, requirement.summary_tokens.count(k) * _keyword_weight(k, preferred_keywords)), filter(lambda k: k in requirement.summary_tokens, keywords_of_stakeholder)))
    # FIXME: wrong preferred_keywords handling !!!
    keyword_occurrences = dict(map(lambda k: (k, int(k in requirement.summary_tokens) * _keyword_weight(k, preferred_keywords)), keywords_of_stakeholder))
    keyword_occurrences_of_existing_keywords = dict(map(lambda k: (k, int(k in requirement.summary_tokens) * _keyword_weight(k, preferred_keywords)), filter(lambda k: k in requirement.summary_tokens, keywords_of_stakeholder)))
    assert(sum(keyword_occurrences_of_existing_keywords.values()) == sum(keyword_occurrences.values()))
    n_keyword_occurrences = sum(keyword_occurrences.values())
    n_keywords_of_stakeholder = len(keywords_of_stakeholder)
    return float(n_keyword_occurrences) / float(n_keywords_of_stakeholder) if n_keywords_of_stakeholder > 0 else 0.0


def compute_contentbased_maut_priority(assignee_email_address: str, user_component_frequencies: Counter,
                                       keywords_of_stakeholder: List[str], preferred_keywords: List[str],
                                       median_results: MedianResults, requirement: Requirement) -> float:
    """
        ==================================
        Without feature scaling:
        ---------------------------------
        Assigned to me:               2.5
        Gerrit Changes:               2.2
        Comments:                     1.9
        CC:                           1.7
        Keywordmatch:                 1.5
        Blocker:                      1.4
        Belongingness of Component:  22.5
        Age (creation):              -6.0
        Age (last update):           -?.? (TODO: consider)
        ==================================


        ==================================
        With feature scaling:
        ----------------------------------
        Assigned to me:               25.0
        Gerrit Changes:               22.0
        Comments:                     19.0
        CC:                           17.0
        Keywordmatch:                 37.5
        Blocker:                      14.0
        Belongingness of Component:   11.5
        Age (creation):              -42.0
        Age (last update):           -?.? (TODO: consider)
        ==================================

    """
    # FIXME: wrong preferred_keywords handling !!!
    #keyword_occurrences = dict(map(lambda k: (k, requirement.summary_tokens.count(k) * _keyword_weight(k, preferred_keywords)), keywords_of_stakeholder))
    #keyword_occurrences_of_existing_keywords = dict(map(lambda k: (k, requirement.summary_tokens.count(k) * _keyword_weight(k, preferred_keywords)), filter(lambda k: k in requirement.summary_tokens, keywords_of_stakeholder)))
    keyword_occurrences = dict(map(lambda k: (k, int(k in requirement.summary_tokens) * _keyword_weight(k, preferred_keywords)), keywords_of_stakeholder))
    keyword_occurrences_of_existing_keywords = dict(map(lambda k: (k, int(k in requirement.summary_tokens) * _keyword_weight(k, preferred_keywords)), filter(lambda k: k in requirement.summary_tokens, keywords_of_stakeholder)))
    assert(sum(keyword_occurrences_of_existing_keywords.values()) == sum(keyword_occurrences.values()))
    n_keyword_occurrences = sum(keyword_occurrences.values())
    n_keywords_of_stakeholder = len(keywords_of_stakeholder)
    responsibility_weight = float(n_keyword_occurrences) / float(n_keywords_of_stakeholder) if n_keywords_of_stakeholder > 0 else 0.0

    #responsibility_weight = max(float(n_keyword_occurrences) / float(n_keywords_of_stakeholder) if n_keywords_of_stakeholder > 0 else 0.0, 0.05)
    n_assigned_to_me = int(requirement.assigned_to == assignee_email_address)

    n_cc_recipients = min(len(requirement.cc) / float(median_results.n_cc_recipients*2.0), 1.0)
    n_blocks = min(len(requirement.blocks) / float(median_results.n_blocks*2.0), 1.0)
    n_gerrit_changes = min(len(requirement.see_also) / float(median_results.n_gerrit_changes*2.0), 1.0)  # TODO: filter only "https://git.eclipse.org/..." URLs

    if requirement.number_of_comments is not None:
        n_comments = min(requirement.number_of_comments / float(median_results.n_comments*2.0), 1.0)
    else:
        n_comments = 0.0

    """
    n_cc_recipients = len(requirement.cc)
    n_blocks = len(requirement.blocks)
    n_gerrit_changes = len(requirement.see_also)

    if requirement.number_of_comments is not None:
        n_comments = requirement.number_of_comments
    else:
        n_comments = 0.0

    creation_date = datetime.strptime(requirement.creation_time, "%Y-%m-%dT%H:%M:%SZ")
    age_in_years = helper.estimated_difference_in_years(creation_date, datetime.now())
    """

    creation_date = datetime.strptime(requirement.creation_time, "%Y-%m-%dT%H:%M:%SZ")
    age_in_years = min(helper.estimated_difference_in_years(creation_date, datetime.now()) / median_results.max_age_years, 1.0)

    """
    print("CC: {}".format(n_cc_recipients))
    print("Blocks: {}".format(n_blocks))
    print("Gerrit: {}".format(n_gerrit_changes))
    print("Comments: {}".format(n_comments))
    print("Age: {}".format(age_in_years))
    print("Median: {}".format(median_results))
    print("-"*80)
    """

    total_component_occurrences = sum(user_component_frequencies.values())
    if total_component_occurrences > 0:
        component_belongingness_degree = user_component_frequencies[requirement.component] / total_component_occurrences
    else:
        component_belongingness_degree = 0.0

    sum_of_dimension_contributions = n_assigned_to_me * 25.0 + n_cc_recipients * 17.0 \
                                   + n_gerrit_changes * 22.0 + n_blocks * 14.0 + n_comments * 19.0 \
                                   + responsibility_weight * 37.5 \
                                   + component_belongingness_degree * 11.5 \
                                   + age_in_years * (-42.0)
    return max(sum_of_dimension_contributions, 0.0)


def _keyword_weight(k, preferred_keywords):
    # TODO: does not work!!
    weight_of_preferred_keyword = 3.0
    return weight_of_preferred_keyword if k in preferred_keywords else 1.0

