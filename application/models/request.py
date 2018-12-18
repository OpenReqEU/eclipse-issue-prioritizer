# coding: utf-8

from __future__ import absolute_import
from typing import List  # noqa: F401
from application.models.base_model_ import Model
from application.util import util


class Request(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """

    def __init__(self, assignee: str=None, components: List[str]=None, products: List[str]=None, keywords: List[str]=None):  # noqa: E501
        """Requirement - a model defined in Swagger

        :param assignee: The email address of the assignee.  # noqa: E501
        :type assignee: str
        :param components: The components to be filtered.  # noqa: E501
        :type components: List[str]
        :param products: The products to be filtered.  # noqa: E501
        :type products: List[str]
        :param keywords: The keywords to be filtered.  # noqa: E501
        :type keywords: List[str]
        """
        self.swagger_types = {
            'assignee': str,
            'components': list,
            'products': list,
            'keywords': list
        }

        self.attribute_map = {
            'assignee': 'assignee',
            'components': 'components',
            'products': 'products',
            'keywords': 'keywords'
        }

        self._assignee = assignee
        self._components = components
        self._products = products
        self._keywords = keywords

    @classmethod
    def from_dict(cls, dikt) -> 'Request':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The Requirement of this Requirement.  # noqa: E501
        :rtype: Requirement
        """
        return util.deserialize_model(dikt, cls)

    def unique_key(self):
        return "{}_#_{}_#_{}_#_{}".format(self.assignee, set(self.components), set(self.products), set(self.keywords))

    @property
    def assignee(self) -> str:
        """Gets the email address of the assignee.


        :return: The email address of the assignee.
        :rtype: str
        """
        return self._assignee

    @assignee.setter
    def assignee(self, assignee: str):
        """Sets the email address of the assignee.


        :param assignee: The assignee.
        :type assignee: str
        """

        self._assignee = assignee

    @property
    def components(self) -> List[str]:
        """Gets the components.


        :return: The components.
        :rtype: List[str]
        """
        return self._components

    @components.setter
    def components(self, components: []):
        """Sets the components.


        :param components: The components list attribute.
        :type components: List[str]
        """

        self._components = components

    @property
    def products(self) -> List[str]:
        """Gets the products.


        :return: The products.
        :rtype: List[str]
        """
        return self._products

    @products.setter
    def products(self, products: []):
        """Sets the products.


        :param products: The products list attribute.
        :type products: List[str]
        """

        self._products = products

    @property
    def keywords(self) -> List[str]:
        """Gets the keywords.


        :return: The keywords.
        :rtype: List[str]
        """
        return self._keywords

    @keywords.setter
    def keywords(self, keywords: []):
        """Sets the keywords.


        :param keywords: The keywords list attribute.
        :type keywords: List[str]
        """

        self._keywords = keywords
