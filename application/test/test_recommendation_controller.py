# coding: utf-8

import os
from application.util import helper
from flask import json
from urllib.parse import urlparse
from application.models.prioritized_recommendations_request import PrioritizedRecommendationsRequest
from application.models.like_requirement_request import LikeRequirementRequest
from application.models.defer_requirement_request import DeferRequirementRequest
from application.models.delete_profile_request import DeleteProfileRequest
from application.models.chart_request import ChartRequest
from application.test import BaseTestCase
from bs4 import BeautifulSoup
import json as js
import pickledb
import warnings
import time


class TestRecommendationController(BaseTestCase):
    """RecommendationController integration tests"""
    def setUp(self):
        helper.init_config()
        self.agent_id = "9ff699c7"
        warnings.filterwarnings("ignore", category=ResourceWarning)
        warnings.filterwarnings("ignore", category=UserWarning)
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        db = pickledb.load(os.path.join(helper.DATA_PATH, "storage.db"), False)
        db.set("VERSION_{}".format(self.agent_id), 0)
        db.dump()

    def tearDown(self):
        pass

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
        self.assertTrue(all(map(lambda r: 0.1 <= r["priority"] <= 100.0, ranked_bugs)))
        for rb in ranked_bugs:
            self.assertIn(rb["component"], expected_components, "Unexpected component: {}".format(rb["component"]))
            self.assertIn(rb["product"], expected_products, "Unexpected product: {}".format(rb["product"]))
            self.assertIsInstance(rb["id"], int)
            self.assertIsInstance(rb["keywords"], list)
            self.assertIsInstance(rb["milestone"], str)
            self.assertIsInstance(rb["numberOfCC"], int)
            self.assertIsInstance(rb["priority"], int)
            # make sure that no requirements are included with priority 1
            self.assertGreaterEqual(rb["priority"], 1)
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
        keywords_line = "{} {}".format(html_content.split("occurrenceData")[1].split("}")[0]
                                       .replace("=", "")[:-2].strip(), " }")
        keywords = js.loads(keywords_line)
        self.assertTrue(len(keywords) > 0)
        self.assertTrue(all(map(lambda t: isinstance(t[0], str), keywords.items())))
        self.assertTrue(all(map(lambda t: isinstance(t[1], int), keywords.items())))

    def test_like_requirement(self):
        assignee = "simon.scholz@vogella.com"
        expected_components = ["UI"]
        expected_products = ["Platform"]
        body = PrioritizedRecommendationsRequest(agent_id=self.agent_id, assignee=assignee,
                                                 components=expected_components, products=expected_products,
                                                 keywords=[])
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
        liked_requirement_id = ranked_bugs[-1]["id"]

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

        body = PrioritizedRecommendationsRequest(agent_id=self.agent_id, assignee=assignee,
                                                 components=expected_components, products=expected_products,
                                                 keywords=[])
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
        self.assertTrue(all(map(lambda r: 0.1 <= r["priority"] <= 100.0, ranked_bugs)))
        self.assertIn(liked_requirement_id, map(lambda r: r["id"], ranked_bugs),
                      "The liked requirement is not part of the ranked list any more!")
        for idx, rb in enumerate(ranked_bugs):
            if rb["id"] == liked_requirement_id:
                self.assertLess(idx, 10)

    def test_unlike_requirement(self):
        assignee = "simon.scholz@vogella.com"
        expected_components = ["UI"]
        expected_products = ["Platform"]
        body = PrioritizedRecommendationsRequest(agent_id=self.agent_id, assignee=assignee,
                                                 components=expected_components, products=expected_products,
                                                 keywords=[])
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
        liked_requirement_id = ranked_bugs[-1]["id"]
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

        body = LikeRequirementRequest(id=liked_requirement_id, agent_id=self.agent_id, assignee=assignee,
                                      components=expected_components, products=expected_products, keywords=[])
        response = self.client.open(
            "/prioritizer/unlike",
            method="POST",
            data=json.dumps(body),
            content_type="application/json")
        self.assert200(response, 'Response body is : ' + response.data.decode('utf-8'))
        response = response.json
        self.assertFalse(response["error"], "An error occurred while processing the request!")
        if "errorMessage" in response:
            self.assertIsNone(response["errorMessage"], "Error message is not empty!")

        body = PrioritizedRecommendationsRequest(agent_id=self.agent_id, assignee=assignee,
                                                 components=expected_components, products=expected_products,
                                                 keywords=[])
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
        self.assertIn(liked_requirement_id, map(lambda r: r["id"], ranked_bugs),
                      "The liked requirement is not part of the ranked list any more!")
        for idx, rb in enumerate(ranked_bugs):
            if rb["id"] == liked_requirement_id:
                self.assertGreater(idx, 10)

    def test_dislike_requirement(self):
        assignee = "simon.scholz@vogella.com"
        expected_components = ["UI", "IDE"]
        expected_products = ["Platform"]
        body = PrioritizedRecommendationsRequest(agent_id=self.agent_id, assignee=assignee,
                                                 components=expected_components,
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
        disliked_requirement_id = ranked_bugs[0]["id"]
        body = LikeRequirementRequest(id=disliked_requirement_id, agent_id=self.agent_id, assignee=assignee,
                                      components=expected_components, products=expected_products, keywords=[])
        response = self.client.open(
            "/prioritizer/dislike",
            method="POST",
            data=json.dumps(body),
            content_type="application/json")
        self.assert200(response, 'Response body is : ' + response.data.decode('utf-8'))
        response = response.json
        self.assertFalse(response["error"], "An error occurred while processing the request!")
        if "errorMessage" in response:
            self.assertIsNone(response["errorMessage"], "Error message is not empty!")

        body = PrioritizedRecommendationsRequest(agent_id=self.agent_id, assignee=assignee,
                                                 components=expected_components,
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
        self.assertTrue(all(map(lambda r: 0.1 <= r["priority"] <= 100.0, ranked_bugs)))
        self.assertNotIn(disliked_requirement_id, map(lambda rb: rb["id"], ranked_bugs),
                         "The disliked requirement is still part of the ranked list!")

    def test_defer_requirement(self):
        assignee = "simon.scholz@vogella.com"
        expected_components = ["UI", "IDE"]
        expected_products = ["Platform"]
        expected_interval = 0.00002314815*2  # 4 seconds (expressed in days)
        body = PrioritizedRecommendationsRequest(agent_id=self.agent_id, assignee=assignee,
                                                 components=expected_components,
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
        deferred_requirement_id = ranked_bugs[0]["id"]
        body = DeferRequirementRequest(id=deferred_requirement_id, agent_id=self.agent_id, interval=expected_interval,
                                       assignee=assignee, components=expected_components, products=expected_products,
                                       keywords=[])
        response = self.client.open(
            "/prioritizer/defer",
            method="POST",
            data=json.dumps(body),
            content_type="application/json")
        self.assert200(response, 'Response body is : ' + response.data.decode('utf-8'))
        response = response.json
        self.assertFalse(response["error"], "An error occurred while processing the request!")
        if "errorMessage" in response:
            self.assertIsNone(response["errorMessage"], "Error message is not empty!")

        body = PrioritizedRecommendationsRequest(agent_id=self.agent_id, assignee=assignee,
                                                 components=expected_components,
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
        self.assertTrue(all(map(lambda r: 0.1 <= r["priority"] <= 100.0, ranked_bugs)))
        self.assertNotIn(deferred_requirement_id, map(lambda rb: rb["id"], ranked_bugs),
                         "The deferred requirement is still part of the ranked list!")

        expected_interval_in_s = expected_interval * 1.5 * 24 * 60 * 60
        time.sleep(expected_interval_in_s)

        body = PrioritizedRecommendationsRequest(agent_id=self.agent_id, assignee=assignee,
                                                 components=expected_components,
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
        self.assertTrue(all(map(lambda r: 0.1 <= r["priority"] <= 100.0, ranked_bugs)))
        self.assertIn(deferred_requirement_id, map(lambda rb: rb["id"], ranked_bugs),
                      "The deferred requirement has not been re-included in the ranked list!")

    def test_delete_user_profile(self):
        body = DeleteProfileRequest(agent_id=self.agent_id)
        response = self.client.open(
            "/prioritizer/profile/delete",
            method="POST",
            data=json.dumps(body),
            content_type="application/json")
        self.assert200(response, 'Response body is : ' + response.data.decode('utf-8'))
        response = response.json
        self.assertFalse(response["error"], "An error occurred while processing the request!")
        if "errorMessage" in response:
            self.assertIsNone(response["errorMessage"], "Error message is not empty!")

        db = pickledb.load(os.path.join(helper.DATA_PATH, "storage.db"), False)
        all_keys = db.getall()
        remaining_keys_containing_agent_id = list(filter(lambda k: self.agent_id in k, all_keys))
        self.assertEqual(len(remaining_keys_containing_agent_id), 0, "No or not all keys were deleted!")
        return response

    def _is_valid_url(self, url):
        try:
            result = urlparse(url)
            self.assertIn(result.scheme, {"http", "https"}, "URL {} is not of scheme http/https".format(url))
            self.assertEqual(result.port, helper.app_port(),
                             "URL {} does not contain application port {}".format(url, helper.app_port()))
            self.assertEqual(result.query, "", "URL {} has empty query".format(url))
            self.assertEqual(result.hostname, helper.app_host(), "URL {} contains wrong host.".format(url, helper.app_host()))
            self.assertRegex(result.path, r'/prioritizer/chart/c/([a-zA-Z0-9]{16})',
                             "Path of URL {} does not conform to the pattern {}".format(url, "/prioritizer/chart/c/([a-zA-Z0-9]{16})"))
            return all([result.scheme, result.netloc, result.path])
        except:
            return False
        """
        self.assertRegex(url, r'/prioritizer/chart/c/([a-zA-Z0-9]{16})',
                         "Path of URL {} does not conform to the pattern {}".format(url, "/prioritizer/chart/c/([a-zA-Z0-9]{16})"))
        return True
        """


if __name__ == "__main__":
    db_path = os.path.join(helper.DATA_PATH, "storage.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    import unittest
    unittest.main()
