# coding: utf-8

from __future__ import absolute_import
from application.models.base_model_ import Model
from application.util import util


class DeleteProfileRequest(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """

    def __init__(self, agent_id: str=None):  # noqa: E501
        """DeleteRequirementRequest - a model defined in Swagger

        :param agent_id: The ID of the agent.  # noqa: E501
        :type agent_id: str
        """
        self.swagger_types = {
            'agent_id': str
        }

        self.attribute_map = {
            'agent_id': 'agent_id'
        }

        self._agent_id = agent_id

    @classmethod
    def from_dict(cls, dikt) -> 'DeleteProfileRequest':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The profile request.  # noqa: E501
        :rtype: DeleteProfileRequest
        """
        return util.deserialize_model(dikt, cls)

    @property
    def agent_id(self) -> str:
        """Gets the agent ID.


        :return: The agent ID.
        :rtype: str
        """
        return self._agent_id

    @agent_id.setter
    def agent_id(self, agent_id: int):
        """Sets the agent ID.


        :param ID: The agent ID.
        :type ID: int
        """

        self._agent_id = agent_id

