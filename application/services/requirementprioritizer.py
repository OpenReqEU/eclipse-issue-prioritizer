# coding: utf-8

from application.models.requirement import Requirement
import logging
from application.services import bugzillafetcher
from application.services import keywordextractor
from dateutil import parser
from flask import json
from datetime import datetime, timedelta
from typing import List  # noqa: F401


_logger = logging.getLogger(__name__)


class RequirementPrioritizer(object):

    def __init__(self, db):
        self.db = db
        self.bugzilla_fetcher = bugzillafetcher.BugzillaFetcher("https://bugs.eclipse.org/bugs/rest/bug")
        self.keyword_extractor = keywordextractor.KeywordExtractor()

    def _reward_liked_requirement(self, agent_id: str, requirement: Requirement):
        like_unique_key = self.db.get("LIKE_{}_{}".format(agent_id, requirement.id))

        if like_unique_key is not False:
            requirement.reward = True

        return requirement

    def _is_relevant_requirement(self, agent_id: str, requirement: Requirement) -> bool:
        dislike_unique_key = self.db.get("DISLIKE_{}_{}".format(agent_id, requirement.id))
        result = self.db.get("DEFER_{}_{}".format(agent_id, requirement.id))
        defer_unique_key = result[0] if result is not False else None
        defer_interval = result[1] if result is not False else ""
        defer_expiration_date = parser.parse(json.loads(result[2])) if result is not False else None
        now = datetime.now()

        if dislike_unique_key is not False:
            return False

        if defer_unique_key is not False and defer_expiration_date is not None and now <= defer_expiration_date:
            return False

        return True

    def compute_user_profile(self, assignee: str, components: List[str], products: List[str], limit: int=800) -> List[str]:
        # compute user profile (based on keywords)
        bugs = self.bugzilla_fetcher.fetch_bugs(assignee, products, components, "RESOLVED", limit=limit)
        requirements = list(map(lambda b: Requirement.from_bug(b), bugs))
        return self.keyword_extractor.extract_keywords(requirements, enable_pos_tagging=False,
                                                       enable_lemmatization=False, lang="en")

    def prioritize(self, agent_id: str, assignee: str, components: List[str], products: List[str],
                   preferred_keywords: List[str]) -> List[Requirement]:
        # advanced content-based recommendation with MAUT
        user_profile_keywords = self.compute_user_profile(assignee=assignee, components=components,
                                                          products=products, limit=800)
        new_bugs = self.bugzilla_fetcher.fetch_bugs(None, products, components, "NEW", limit=75)
        new_requirements = list(map(lambda b: Requirement.from_bug(b), new_bugs))
        new_requirements = list(filter(lambda r: self._is_relevant_requirement(agent_id, r), new_requirements))
        new_requirements = list(map(lambda r: self._reward_liked_requirement(agent_id, r), new_requirements))
        self.keyword_extractor.extract_keywords(new_requirements, enable_pos_tagging=False,
                                                enable_lemmatization=False, lang="en")

        # FIXME: fails for tests!
        """
        bug_comments = self.bugzilla_fetcher.fetch_comments_parallelly(list(map(lambda r: r.id, new_requirements)))
        """
        bug_comments = {}
        for r in new_requirements: bug_comments[r.id] = self.bugzilla_fetcher.fetch_comments(r.id)

        for r in new_requirements:
            comments = bug_comments[r.id]
            r.number_of_comments = len(comments)

        version = 0
        total_sum_of_priorities = 0.0
        for r in new_requirements:
            if version == 0:
                r.computed_priority = compute_contentbased_maut_priority(assignee, user_profile_keywords, preferred_keywords, r)
            elif version == 1:
                r.computed_priority = compute_contentbased_priority(user_profile_keywords, preferred_keywords, r)
            r.computed_priority = r.computed_priority * (100 if r.reward else 1)
            #else:
            #    r.computed_priority = compute_collaborative_priority(request.assignee, user_extracted_keywords, preferred_keywords, r)
            total_sum_of_priorities += r.computed_priority

        for r in new_requirements:
            r.computed_priority *= 100.0 / total_sum_of_priorities

        new_requirements = filter(lambda r: r.computed_priority >= 0.01, new_requirements)
        return sorted(new_requirements, key=lambda r: r.computed_priority, reverse=True)


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


def compute_contentbased_maut_priority(assignee_email_address: str, keywords_of_stakeholder: List[str],
                                       preferred_keywords: List[str], requirement: Requirement) -> float:
    """
        Assigned to me:    2.5
        Gerrit Changes:    2.2
        Comments:          1.9
        CC:                1.7
        Blocker:           1.4
    """
    # FIXME: wrong preferred_keywords handling !!!
    #keyword_occurrences = dict(map(lambda k: (k, requirement.summary_tokens.count(k) * _keyword_weight(k, preferred_keywords)), keywords_of_stakeholder))
    #keyword_occurrences_of_existing_keywords = dict(map(lambda k: (k, requirement.summary_tokens.count(k) * _keyword_weight(k, preferred_keywords)), filter(lambda k: k in requirement.summary_tokens, keywords_of_stakeholder)))
    keyword_occurrences = dict(map(lambda k: (k, int(k in requirement.summary_tokens) * _keyword_weight(k, preferred_keywords)), keywords_of_stakeholder))
    keyword_occurrences_of_existing_keywords = dict(map(lambda k: (k, int(k in requirement.summary_tokens) * _keyword_weight(k, preferred_keywords)), filter(lambda k: k in requirement.summary_tokens, keywords_of_stakeholder)))
    assert(sum(keyword_occurrences_of_existing_keywords.values()) == sum(keyword_occurrences.values()))
    n_keyword_occurrences = sum(keyword_occurrences.values())
    n_keywords_of_stakeholder = len(keywords_of_stakeholder)
    responsibility_weight = max(float(n_keyword_occurrences) / float(n_keywords_of_stakeholder) if n_keywords_of_stakeholder > 0 else 0.0, 0.05)
    n_assigned_to_me = int(requirement.assigned_to == assignee_email_address)
    n_cc_recipients = len(requirement.cc)
    n_blocks = len(requirement.blocks)
    n_gerrit_changes = len(requirement.see_also) # TODO: filter only "https://git.eclipse.org/..." URLs
    n_comments = requirement.number_of_comments

    # TODO: this must be normalized (calculate the mean and take the difference to the mean value into account)
    #       ---> feature scaling (evaluate complete feature range for all requirements dimension-wise)
    sum_of_dimension_contributions = n_assigned_to_me * 2.5 + n_cc_recipients * 1.7 \
                                   + n_gerrit_changes * 2.2 + n_blocks * 1.4 + n_comments * 1.9
    return sum_of_dimension_contributions * responsibility_weight


def _keyword_weight(k, preferred_keywords):
    # TODO: does not work!!
    weight_of_preferred_keyword = 3.0
    return weight_of_preferred_keyword if k in preferred_keywords else 1.0

