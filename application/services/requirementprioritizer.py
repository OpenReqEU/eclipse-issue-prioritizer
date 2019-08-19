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

UserProfile = collections.namedtuple("UserProfile", [
    "assignee_email_address",
    "component_frequencies",
    "keyword_frequencies"
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

    def _compute_user_profile(self, assignee: str, components: List[str], products: List[str],
                              limit: int=0, max_age_years: int=7) -> (Counter, Counter):
        # compute user profile (based on keywords)
        bugs = self.bugzilla_fetcher.fetch_bugs(assignee, products, components, "RESOLVED", limit=limit,
                                                max_age_years=max_age_years)
        requirements = list(map(lambda b: Requirement.from_bug(b), bugs))
        components = list(map(lambda r: r.component, requirements))
        self.keyword_extractor.extract_keywords(requirements, lang="en")
        component_frequencies = Counter(components)
        keyword_frequencies = Counter([t for r in requirements for t in r.summary_tokens])
        return component_frequencies, keyword_frequencies

    def fetch_and_prioritize(self, agent_id: str, assignee: str, components: List[str], products: List[str],
                             preferred_keywords: List[str], limit: int, max_age_years: int,
                             version: int) -> (List[Requirement], UserProfile):
        # advanced content-based recommendation with MAUT
        component_frequencies, keyword_frequencies = self._compute_user_profile(assignee, components, products,
                                                                                0, max_age_years)
        new_bugs = self.bugzilla_fetcher.fetch_bugs(None, products, components, "NEW", max_age_years=max_age_years)
        new_requirements = list(map(lambda b: Requirement.from_bug(b), new_bugs))
        user_profile = UserProfile(assignee_email_address=assignee, component_frequencies=component_frequencies,
                                   keyword_frequencies=keyword_frequencies)

        # since we have to deal with a large number of issues, the number of request to fetch the issues' comments
        # must be limited -> therefore we prioritize the issues without taking the comments into account
        # and only consider the 75 top-most issues with the highest priority. Only for these issues we fetch
        # the comments and finally do the final prioritization where we also take into account the comments.
        new_requirements, is_version_redirect = self.prioritize(agent_id=agent_id, requirements=new_requirements,
                                                                user_profile=user_profile,
                                                                preferred_keywords=preferred_keywords,
                                                                max_age_years=max_age_years, version=version)
        new_requirements = new_requirements[:limit]

        bug_comments = self.bugzilla_fetcher.fetch_comments_parallelly(list(map(lambda r: r.id, new_requirements)))
        for r in new_requirements:
            comments = bug_comments[r.id]
            r.number_of_comments = len(comments)

        sorted_requirements, temp = self.prioritize(agent_id=agent_id, requirements=new_requirements,
                                                    user_profile=user_profile, preferred_keywords=preferred_keywords,
                                                    max_age_years=max_age_years, version=version)
        assert(temp == is_version_redirect)
        return sorted_requirements, user_profile, is_version_redirect

    def prioritize(self, agent_id: str, requirements: List[Requirement], user_profile: UserProfile,
                   preferred_keywords: List[str], max_age_years: int, version: int) -> List[Requirement]:
        requirements = list(filter(lambda r: self._is_relevant_requirement(agent_id, r), requirements))
        requirements = list(map(lambda r: self._reward_liked_requirement(agent_id, r), requirements))
        self.keyword_extractor.extract_keywords(requirements, lang="en")
        median_n_cc_recipients = max(np.median(list(map(lambda r: len(r.cc), requirements))), 1e-2)
        median_n_blocks = max(np.median(list(map(lambda r: len(r.blocks), requirements))), 1e-2)  # TODO: filter only "https://git.eclipse.org/..." URLs
        median_n_gerrit_changes = max(np.median(list(map(lambda r: len(r.see_also), requirements))), 1e-2)
        median_n_comments = max(np.median(list(map(lambda r: r.number_of_comments or 0.0, requirements))), 1e-2)
        keyword_contributions = list(map(lambda r: _compute_contentbased_priority(user_profile.keyword_frequencies, preferred_keywords, r), requirements))
        max_keyword_contributions, min_keyword_contributions = max(keyword_contributions), min(keyword_contributions)
        is_version_redirect = False
        if max_keyword_contributions - min_keyword_contributions > 0:
            keyword_contributions = list(map(lambda v: (v - min_keyword_contributions)/(max_keyword_contributions - min_keyword_contributions), keyword_contributions))
        else:
            keyword_contributions = np.zeros(len(requirements))
            version = 0  # redirect to content-based MAUT version since the user is a newcomer (no keywords in profile)
            is_version_redirect = True
        median_results = MedianResults(n_cc_recipients=median_n_cc_recipients, n_blocks=median_n_blocks,
                                       n_gerrit_changes=median_n_gerrit_changes, n_comments=median_n_comments,
                                       max_age_years=max_age_years)

        max_priority = 0.0
        for idx, r in enumerate(requirements):
            if version == 0:
                r.computed_priority = _compute_contentbased_maut_priority(keyword_contributions[idx], user_profile,
                                                                          median_results, r)
            elif version == 1:
                r.computed_priority = (keyword_contributions[idx] + 0.1) if r.reward else keyword_contributions[idx]

            if r.computed_priority > max_priority:
                max_priority = r.computed_priority

        for r in requirements:
            r.computed_priority = max(r.computed_priority * 100.0 / max_priority, 1.0) if max_priority > 0.0 else 1.0

        requirements = filter(lambda r: r.computed_priority >= 0.01, requirements)
        return sorted(requirements, key=lambda r: r.computed_priority, reverse=True), is_version_redirect


def _compute_contentbased_priority(keyword_frequencies: Counter, preferred_keywords: List[str], requirement: Requirement) -> float:
    # FIXME: preferred_keywords handling is suboptimal!!!
    total_keyword_frequencies = sum(keyword_frequencies.values())
    requ_tokens = requirement.summary_tokens
    if total_keyword_frequencies == 0 or len(requ_tokens) == 0:
        return 0.0

    keyword_contributions = 0.0
    for (k, f) in keyword_frequencies.items():
        keyword_contributions += requ_tokens.count(k) * f * _keyword_weight(k, preferred_keywords)

    return keyword_contributions / float(len(requ_tokens) * total_keyword_frequencies)


def _compute_contentbased_maut_priority(keywords_contribution: float, user_profile: UserProfile,
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
        Keywordmatch:                 28.0
        Blocker:                      14.0
        Belongingness of Component:   11.5
        Liked requirement:            20.5
        Age (creation):              -42.0
        Age (last update):           -?.? (TODO: consider)
        ==================================

    """
    n_assigned_to_me = int(requirement.assigned_to == user_profile.assignee_email_address)

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

    total_component_occurrences = sum(user_profile.component_frequencies.values())
    if total_component_occurrences > 0:
        component_belongingness_degree = user_profile.component_frequencies[requirement.component] / total_component_occurrences
    else:
        component_belongingness_degree = 0.0

    severity_map = {
        'blocker': 6,
        'critical': 5,
        'major': 4,
        'normal': 3,
        'minor': 2,
        'trivial': 1,
        'enhancement': 0
    }

    priority_map = {
        'P1': 4,
        'P2': 3,
        'P3': 2,
        'P4': 1,
        'P5': 0
    }

    weights = {
        "assigned_to": 2.50,
        "cc": 1.70,
        "gerrit": 2.20,
        "blocks": 1.40,
        "comments": 1.90,
        "keywords": 2.80,
        "component_belongingness": 2.80,
        "reward": 2.00,
        "severity": 1.80,
        "priority": 2.20,
        "age": -4.20
    }

    sum_of_dimension_contributions = n_assigned_to_me * weights["assigned_to"] \
                                   + n_cc_recipients * weights["cc"] \
                                   + n_gerrit_changes * weights["gerrit"] \
                                   + n_blocks * weights["blocks"] \
                                   + n_comments * weights["comments"] \
                                   + keywords_contribution * weights["keywords"] \
                                   + severity_map[requirement.severity] * weights["severity"] \
                                   + priority_map[requirement.priority] * weights["priority"] \
                                   + component_belongingness_degree * weights["component_belongingness"] \
                                   + int(requirement.reward) * weights["reward"] \
                                   + age_in_years * weights["age"]
    return max(sum_of_dimension_contributions, 0.0)


def _keyword_weight(k, preferred_keywords):
    weight_of_preferred_keyword = 3.0
    return weight_of_preferred_keyword if k in preferred_keywords else 1.0

