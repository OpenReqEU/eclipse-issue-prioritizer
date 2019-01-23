# coding: utf-8

from __future__ import absolute_import
from flask import json
from urllib.parse import urlparse
from application.models.prioritized_recommendations_request import PrioritizedRecommendationsRequest
from application.models.like_requirement_request import LikeRequirementRequest
from application.models.chart_request import ChartRequest
from application.util import helper
from application.test import BaseTestCase
from bs4 import BeautifulSoup
import json as js


class TestRecommendationController(BaseTestCase):
    """RecommendationController integration tests"""
    def setUp(self):
        helper.init_config()
        self.agent_id = "9ff699c7-94de-4105-9f74-0107653daa89"

    def test_compute_prioritization(self):
        expected_components = ["UI", "IDE"]
        expected_products = ["Platform"]
        body = PrioritizedRecommendationsRequest(agent_id=self.agent_id, assignee="simon.scholz@vogella.com",
                                                 components=expected_components, products=expected_products, keywords=[])
        response = self.client.open(
            "/prioritizer/compute",
            method="POST",
            data=json.dumps(body),
            content_type="application/json")
        self.assert200(response, 'Response body is : ' + response.data.decode('utf-8'))
        response = response.json
        self.assertFalse(response["error"], "An error occurred while processing the request!")
        if "errorMessage" in response:
            self.assertIsNone(response["errorMessage"], "Error message is not empty!")
        ranked_bugs = response["rankedBugs"]
        self.assertIsInstance(ranked_bugs, list)
        self.assertTrue(len(ranked_bugs) > 0, "List of prioritizes requirements is empty!")
        self.assertAlmostEqual(sum(map(lambda rb: rb["priority"], ranked_bugs)), 100.0, delta=0.1)
        for rb in ranked_bugs:
            self.assertIn(rb["component"], expected_components, "Unexpected component: {}".format(rb["component"]))
            self.assertIn(rb["product"], expected_products, "Unexpected product: {}".format(rb["product"]))
            self.assertIsInstance(rb["id"], int)
            self.assertIsInstance(rb["keywords"], list)
            self.assertIsInstance(rb["milestone"], str)
            self.assertIsInstance(rb["numberOfCC"], int)
            self.assertIsInstance(rb["priority"], float)
            # make sure that no requirements are included with priority 0.0
            self.assertGreaterEqual(rb["priority"], 0.01)
            self.assertIsInstance(rb["summary"], str)

        # make sure that requirement summaries contain uppercase letters (i.e., are not lowercased by the prioritizer)
        self.assertTrue(any(c.isupper() for rb in ranked_bugs for c in rb["summary"]))

    def test_generate_chart_url(self):
        expected_components = ["UI", "IDE"]
        expected_products = ["Platform"]
        body = ChartRequest(agent_id=self.agent_id, assignee="simon.scholz@vogella.com", components=expected_components,
                            products=expected_products, keywords=[])
        response = self.client.open(
            "/prioritizer/chart",
            method="POST",
            data=json.dumps(body),
            content_type="application/json")
        self.assert200(response, 'Response body is : ' + response.data.decode('utf-8'))
        response = response.json
        self.assertFalse(response["error"], "An error occurred while processing the request!")
        if "errorMessage" in response:
            self.assertIsNone(response["errorMessage"], "Error message is not empty!")
        url = response["url"]
        self.assertIsInstance(url, str)
        self.assertTrue(self._is_valid_url(url), "Invalid URL {}".format(url))

    def test_cached_chart_url(self):
        expected_components = ["UI", "IDE"]
        expected_products = ["Platform"]
        body = ChartRequest(agent_id=self.agent_id, assignee="simon.scholz@vogella.com", components=expected_components,
                            products=expected_products, keywords=[])
        response = self.client.open(
            "/prioritizer/chart",
            method="POST",
            data=json.dumps(body),
            content_type="application/json")
        self.assert200(response, 'Response body is : ' + response.data.decode('utf-8'))
        response = response.json
        self.assertFalse(response["error"], "An error occurred while processing the request!")
        if "errorMessage" in response:
            self.assertIsNone(response["errorMessage"], "Error message is not empty!")
        previous_url = response["url"]
        self.assertIsInstance(previous_url, str)
        self.assertTrue(self._is_valid_url(previous_url), "Invalid URL {}".format(previous_url))

        response = self.client.open(
            "/prioritizer/chart",
            method="POST",
            data=json.dumps(body),
            content_type="application/json")
        self.assert200(response, 'Response body is : ' + response.data.decode('utf-8'))
        response = response.json
        self.assertFalse(response["error"], "An error occurred while processing the request!")
        if "errorMessage" in response:
            self.assertIsNone(response["errorMessage"], "Error message is not empty!")
        url = response["url"]
        self.assertIsInstance(url, str)
        self.assertTrue(self._is_valid_url(url), "Invalid URL {}".format(url))
        self.assertEqual(url, previous_url, "Unexpected cache miss! The current chart URL {} does not match the "
                                            "previous chart URL {} for the same request".format(url, previous_url))

    def test_not_cached_chart_url(self):
        expected_components = ["UI", "IDE"]
        expected_products = ["Platform"]
        body = ChartRequest(agent_id=self.agent_id, assignee="simon.scholz@vogella.com", components=expected_components,
                            products=expected_products, keywords=[])
        response = self.client.open(
            "/prioritizer/chart",
            method="POST",
            data=json.dumps(body),
            content_type="application/json")
        self.assert200(response, 'Response body is : ' + response.data.decode('utf-8'))
        response = response.json
        self.assertFalse(response["error"], "An error occurred while processing the request!")
        if "errorMessage" in response:
            self.assertIsNone(response["errorMessage"], "Error message is not empty!")
        previous_url = response["url"]
        self.assertIsInstance(previous_url, str)
        self.assertTrue(self._is_valid_url(previous_url), "Invalid URL {}".format(previous_url))

        expected_components = ["UI"]
        body = ChartRequest(agent_id=self.agent_id, assignee="simon.scholz@vogella.com", components=expected_components,
                            products=expected_products, keywords=[])
        response = self.client.open(
            "/prioritizer/chart",
            method="POST",
            data=json.dumps(body),
            content_type="application/json")
        self.assert200(response, 'Response body is : ' + response.data.decode('utf-8'))
        response = response.json
        self.assertFalse(response["error"], "An error occurred while processing the request!")
        if "errorMessage" in response:
            self.assertIsNone(response["errorMessage"], "Error message is not empty!")
        url = response["url"]
        self.assertIsInstance(url, str)
        self.assertTrue(self._is_valid_url(url), "Invalid URL {}".format(url))
        self.assertNotEqual(url, previous_url, "Unexpected cache hit! The current chart URL {} should not match the "
                                               "previous chart URL {} for a modified request".format(url, previous_url))

    def test_chart(self):
        assignee = "simon.scholz@vogella.com"
        expected_components = ["UI", "IDE"]
        expected_products = ["Platform"]
        body = ChartRequest(agent_id=self.agent_id, assignee=assignee, components=expected_components,
                            products=expected_products, keywords=[])
        response = self.client.open(
            "/prioritizer/chart",
            method="POST",
            data=json.dumps(body),
            content_type="application/json")
        self.assert200(response, 'Response body is : ' + response.data.decode('utf-8'))
        response = response.json
        self.assertFalse(response["error"], "An error occurred while processing the request!")
        if "errorMessage" in response:
            self.assertIsNone(response["errorMessage"], "Error message is not empty!")
        url = response["url"]
        self.assertIsInstance(url, str)
        self.assertTrue(self._is_valid_url(url), "Invalid URL {}".format(url))
        url = urlparse(url).path
        response = self.client.open(url, method="GET")
        self.assert200(response, 'Response body is : ' + response.data.decode('utf-8'))
        html_content = response.data.decode('utf-8')
        doc = BeautifulSoup(html_content)
        h1 = doc.find_all("h1")[0]
        self.assertEqual(h1.get_text(), "Keywords of {}".format(assignee))
        keywords_line = "{} {}".format(html_content.split("occurrenceData")[1].split("}")[0].replace("=", "")[:-2].strip(), " }")
        keywords = js.loads(keywords_line)
        self.assertTrue(len(keywords) > 0)
        self.assertTrue(all(map(lambda t: isinstance(t[0], str), keywords.items())))
        self.assertTrue(all(map(lambda t: isinstance(t[1], int), keywords.items())))

    def test_like_requirement(self):
        assignee = "simon.scholz@vogella.com"
        expected_components = ["UI", "IDE"]
        expected_products = ["Platform"]
        liked_requirement_id = 67151
        body = LikeRequirementRequest(id=liked_requirement_id, agent_id=self.agent_id, assignee=assignee,
                                      components=expected_components, products=expected_products, keywords=[])
        response = self.client.open(
            "/prioritizer/like",
            method="POST",
            data=json.dumps(body),
            content_type="application/json")
        self.assert200(response, 'Response body is : ' + response.data.decode('utf-8'))
        response = response.json
        self.assertFalse(response["error"], "An error occurred while processing the request!")
        if "errorMessage" in response:
            self.assertIsNone(response["errorMessage"], "Error message is not empty!")

        """
        body = PrioritizedRecommendationsRequest(agent_id=self.agent_id, assignee=assignee,
                                                 components=expected_components, products=expected_products, keywords=[])
        response = self.client.open(
            "/prioritizer/compute",
            method="POST",
            data=json.dumps(body),
            content_type="application/json")
        self.assert200(response, 'Response body is : ' + response.data.decode('utf-8'))
        response = response.json
        self.assertFalse(response["error"], "An error occurred while processing the request!")
        if "errorMessage" in response:
            self.assertIsNone(response["errorMessage"], "Error message is not empty!")
        ranked_bugs = response["rankedBugs"]
        self.assertIsInstance(ranked_bugs, list)
        self.assertTrue(len(ranked_bugs) > 0, "List of prioritizes requirements is empty!")
        self.assertAlmostEqual(sum(map(lambda rb: rb["priority"], ranked_bugs)), 100.0, delta=0.1)
        for idx, rb in enumerate(ranked_bugs):
            if rb["id"] == liked_requirement_id:
                self.assertLess(idx, 10)
        """

    ## TODO:
    ## 2) Test für User Profile löschen schreiben!!

    def _is_valid_url(self, url):
        try:
            result = urlparse(url)
            self.assertIn(result.scheme, {"http", "https"}, "URL {} is not of scheme http/https".format(url))
            self.assertEqual(result.port, helper.app_port(),
                             "URL {} does not contain application port {}".format(url, helper.app_port()))
            self.assertEqual(result.query, "", "URL {} has empty query".format(url))
            self.assertEqual(result.hostname, helper.app_host(), "URL {} contains wrong host.".format(url, helper.app_host()))
            self.assertRegex(result.path, r'/prioritizer/chart/c/([a-zA-Z0-9]{16})',
                             "Path of URL {} does not conform to pattern".format(url, "/prioritizer/chart/c/([a-zA-Z0-9]{16})"))
            return all([result.scheme, result.netloc, result.path])
        except:
            return False


if __name__ == "__main__":
    import unittest
    unittest.main()
