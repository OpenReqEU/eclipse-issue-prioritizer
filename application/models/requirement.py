# coding: utf-8

from __future__ import absolute_import
from application.models.base_model_ import Model
from application.services.bugzillafetcher import Bug
from application.util import util
from datetime import datetime as dt


class Requirement(Model):
    """
        #is_cc_accessible,
        #groups,
        #qa_contact,
        #dupe_of,
        #cc_detail,
        #op_sys,
        #alias,
        #flags,
        #url,
        #is_confirmed,
        #assigned_to_detail,
        #deadline,
        #is_creator_accessible,
        #creator,
        #classification,
        #keywords,
        #whiteboard
    """

    def __init__(self, id: int, assigned_to: str, status: str, creator: str, summary: str,
                 platform: str, product: str, component: str):
        current_time = dt.now()
        self._id = id
        self._assigned_to = assigned_to
        self._resolution = None
        self._is_open = None
        self._status = status
        self._creator = creator
        self._summary = summary
        self._new_summary = summary
        self._summary_tokens = []
        self._platform = platform
        self._product = product
        self._component = component
        self._severity = None
        self._priority = None
        self._computed_priority = None
        self._version = None
        self._creation_time = None
        self._cc = None
        self._blocks = None
        self._bugzilla_keywords = None
        self._see_also = None
        self._target_milestone = None
        self._number_of_comments = None
        self._depends_on = None
        self._reward = False
        self._last_updated_date = current_time
        self._last_change_time = None

    @classmethod
    def from_dict(cls, dikt) -> 'Requirement':
        return util.deserialize_model(dikt, cls)

    @classmethod
    def from_bug(cls, bug: Bug) -> 'Requirement':
        requirement = Requirement(bug.id, bug.assigned_to, bug.status, bug.creator, bug.summary,
                                  bug.platform, bug.product, bug.component)
        requirement.is_open = bug.is_open
        requirement.version = bug.version
        requirement.depends_on = bug.depends_on
        requirement.severity = bug.severity
        requirement.resolution = bug.resolution
        requirement.see_also = bug.see_also
        requirement.target_milestone = bug.target_milestone
        requirement.priority = bug.priority
        requirement.creator = bug.creator
        requirement.blocks = bug.blocks
        requirement.cc = bug.cc
        requirement.computed_priority = 0.0
        requirement.reward = False
        requirement.creation_time = bug.creation_time
        requirement.last_change_time = bug.last_change_time
        return requirement

    @property
    def id(self):
        return self._id

    @property
    def assigned_to(self):
        return self._assigned_to

    @property
    def resolution(self):
        return self._resolution

    @property
    def is_open(self):
        return self._is_open

    @property
    def status(self):
        return self._status

    @property
    def creator(self):
        return self._creator

    @property
    def summary(self):
        return self._summary

    @property
    def new_summary(self):
        return self._new_summary

    @property
    def summary_tokens(self):
        return self._summary_tokens

    @property
    def platform(self):
        return self._platform

    @property
    def product(self):
        return self._product

    @property
    def component(self):
        return self._component

    @property
    def severity(self):
        return self._severity

    @property
    def priority(self):
        return self._priority

    @property
    def computed_priority(self):
        return self._computed_priority

    @property
    def version(self):
        return self._version

    @property
    def creation_time(self):
        return self._creation_time

    @property
    def cc(self):
        return self._cc

    @property
    def blocks(self):
        return self._blocks

    @property
    def bugzilla_keywords(self):
        return self._bugzilla_keywords

    @property
    def see_also(self):
        return self._see_also

    @property
    def target_milestone(self):
        return self._target_milestone

    @property
    def number_of_comments(self):
        return self._number_of_comments

    @property
    def depends_on(self):
        return self._depends_on

    @property
    def reward(self):
        return self._reward

    @property
    def last_updated_date(self):
        return self._last_updated_date

    @property
    def last_change_time(self):
        return self._last_change_time

    @id.setter
    def id(self):
        return self._id

    @assigned_to.setter
    def assigned_to(self, assigned_to):
        self._assigned_to = assigned_to

    @resolution.setter
    def resolution(self, resolution):
        self._resolution = resolution

    @is_open.setter
    def is_open(self, is_open):
        self._is_open = is_open

    @status.setter
    def status(self, status):
        self._status = status

    @creator.setter
    def creator(self, creator):
        self._creator = creator

    @summary.setter
    def summary(self, summary):
        self._summary = summary

    @new_summary.setter
    def new_summary(self, new_summary):
        self._new_summary = new_summary

    @summary_tokens.setter
    def summary_tokens(self, summary_tokens):
        self._summary_tokens = summary_tokens

    @platform.setter
    def platform(self, platform):
        self._platform = platform

    @product.setter
    def product(self, product):
        self._product = product

    @component.setter
    def component(self, component):
        self._component = component

    @severity.setter
    def severity(self, severity):
        self._severity = severity

    @priority.setter
    def priority(self, priority):
        self._priority = priority

    @computed_priority.setter
    def computed_priority(self, computed_priority):
        self._computed_priority = computed_priority

    @version.setter
    def version(self, version):
        self._version = version

    @creation_time.setter
    def creation_time(self, creation_time):
        self._creation_time = creation_time

    @cc.setter
    def cc(self, cc):
        self._cc = cc

    @blocks.setter
    def blocks(self, blocks):
        self._blocks = blocks

    @bugzilla_keywords.setter
    def bugzilla_keywords(self, bugzilla_keywords):
        self._bugzilla_keywords = bugzilla_keywords

    @see_also.setter
    def see_also(self, see_also):
        self._see_also = see_also

    @target_milestone.setter
    def target_milestone(self, target_milestone):
        self._target_milestone = target_milestone

    @number_of_comments.setter
    def number_of_comments(self, number_of_comments):
        self._number_of_comments = number_of_comments

    @depends_on.setter
    def depends_on(self, depends_on):
        self._depends_on = depends_on

    @reward.setter
    def reward(self, reward):
        self._reward = reward

    @last_updated_date.setter
    def last_updated_date(self, last_updated_date):
        self._last_updated_date = last_updated_date

    @last_change_time.setter
    def last_change_time(self, last_change_time):
        self._last_change_time = last_change_time

