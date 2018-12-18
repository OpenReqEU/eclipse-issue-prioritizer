# coding: utf-8

from __future__ import absolute_import
from flask import json
from urllib.parse import urlparse
from application.models.request import Request
from application.util import helper
from application.test import BaseTestCase
from bs4 import BeautifulSoup
import json as js


class TestRecommendationController(BaseTestCase):
    """RecommendationController integration tests"""

    def test_compute_prioritization(self):
        expected_components = ["UI", "IDE"]
        expected_products = ["Platform"]
        body = Request(assignee="simon.scholz@vogella.com", components=expected_components,
                       products=expected_products, keywords=[])
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
            self.assertIsInstance(rb["keywords"], list)
            self.assertIsInstance(rb["milestone"], str)
            self.assertIsInstance(rb["numberOfCC"], int)
            self.assertIsInstance(rb["priority"], float)
            self.assertIsInstance(rb["summary"], str)

    def test_generate_chart_url(self):
        expected_components = ["UI", "IDE"]
        expected_products = ["Platform"]
        body = Request(assignee="simon.scholz@vogella.com", components=expected_components,
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
        body = Request(assignee="simon.scholz@vogella.com", components=expected_components,
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
        body = Request(assignee="simon.scholz@vogella.com", components=expected_components,
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
        body = Request(assignee="simon.scholz@vogella.com", components=expected_components,
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
        body = Request(assignee=assignee, components=expected_components,
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
