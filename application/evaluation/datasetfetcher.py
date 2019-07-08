# coding: utf-8

from application.models.requirement import Requirement
from application.services import bugzillafetcher
from application.util import helper
from collections import namedtuple
import logging
import urllib.parse
import requests
import time
import datetime
import math
import traceback
import pickledb
import os


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) AppleWebKit/604.3.9 (KHTML, like Gecko) Version/12.0.2 Safari/601.3.9",
    "Accept": "application/json"
}
_logger = logging.getLogger(__name__)


class DatasetFetcher(object):

    def __init__(self, db, dataset_name, base_url, dataset_file_path):
        self._db = db
        self._dataset_name = dataset_name
        self._base_url = base_url
        self._dataset_file_path = dataset_file_path

    def _print_product_list(self, product_names):
        n_product_names = len(product_names)
        _logger.info("List of all {} products:".format(n_product_names))
        _logger.info("-" * 80)
        for product_name in product_names:
            _logger.info("   - {}".format(product_name))
        _logger.info("-" * 80)

    def download_requirements_of_last_n_years(self, n: int=3, status: str=None):
        ########################################################################
        # Fetch products & components
        ########################################################################
        url = "{}/{}".format(self._base_url, "product?type=accessible")
        _logger.info("Fetching products and components from: {}".format(url))
        bugzilla_fetcher = bugzillafetcher.BugzillaFetcher("{}/{}".format(self._base_url, "bug"))
        r = requests.get(url, headers=HEADERS)
        r.raise_for_status()
        parsed_data = r.json()
        products_data = parsed_data["products"]
        product_names = list(map(lambda d: d["name"], products_data))
        self._print_product_list(product_names)

        ########################################################################
        # Fetch issues & comments
        ########################################################################
        remaining_product_names = set()
        requirements = {}
        counter = 0
        max_http_repeat = 10
        for product_name, product_data in zip(product_names, products_data):
            _logger.info("Product: {} ({:.1%})".format(product_name, float(counter) / float(len(product_names))))
            n_max_bugs_limit = 1000
            pbugs = []
            n_pbugs_old = 0
            for component_data in product_data["components"]:
                _logger.info("  Component: {}".format(component_data["name"]))
                last_response = None
                offset = 0
                while last_response is None or len(last_response) > 0:
                    last_response = self._fetch_bugs_of_product_and_component(n, product_name, status,
                                                                              component_data["name"],
                                                                              n_max_bugs_limit, offset)
                    if len(last_response) > 0:
                        pbugs += last_response
                    offset += n_max_bugs_limit
                _logger.info("    Number of fetched bugs: {}".format(len(pbugs) - n_pbugs_old))
                _logger.info("")
                n_pbugs_old = len(pbugs)

            prequirements = list(map(lambda b: Requirement.from_bug(b), pbugs))
            """
            if len(prequirements) > 0:
                if self._dataset_name == "mozilla":
                    _logger.info("Fetching all comments for {} requirements...".format(len(prequirements)))
                    bug_comments = {}
                    for bug_id in set(map(lambda r: r.id, prequirements)):
                        n_repeat = 0
                        while n_repeat < max_http_repeat:
                            try:
                                bug_comments[int(bug_id)] = bugzilla_fetcher.fetch_comments(bug_id)
                                _logger.info("  Number of fetched comments: {}".format(len(bug_comments)))
                                time.sleep(0.25)
                                break
                            except Exception as e:
                                wait_time_in_seconds = math.pow(2, n_repeat)
                                _logger.error("    {}".format(traceback.format_exc()))
                                _logger.info("    Request(s) failed... Try again in {} seconds...".format(wait_time_in_seconds))
                                time.sleep(wait_time_in_seconds)
                                n_repeat += 1
                                continue
                else:
                    _logger.info("Fetching all comments for {} requirements in parallel...".format(len(prequirements)))
                    n_repeat = 0
                    while n_repeat < max_http_repeat:
                        try:
                            bug_comments = bugzilla_fetcher.fetch_comments_parallelly(list(set(map(lambda r: r.id, prequirements))), n_max_workers=16)
                            _logger.info("  Number of fetched comments: {}".format(len(bug_comments)))
                            break
                        except Exception as e:
                            wait_time_in_seconds = math.pow(2, n_repeat)
                            _logger.error("    {}".format(traceback.format_exc()))
                            _logger.info("    Request(s) failed... Try again in {} seconds...".format(wait_time_in_seconds))
                            time.sleep(wait_time_in_seconds)
                            n_repeat += 1
                            continue

                for r in prequirements:
                    comments = bug_comments[r.id]
                    r.comments = comments
                    r.number_of_comments = len(comments)
            """

            self._db = pickledb.load(os.path.join(helper.DATA_PATH, "storage.db"), False)
            n_requirements_before = len(requirements)
            for r in prequirements:
                requirements[r.id] = r

            n_requirements_now = len(requirements)
            _logger.info("Requirements for this product: {}".format((n_requirements_now - n_requirements_before)))
            remaining_product_names.add(product_name)
            counter += 1
            _logger.info("-" * 80)
            _logger.info("")

        _logger.info("-" * 80)
        _logger.info("Number of total bugs: {}".format(len(requirements)))
        _logger.info("-" * 80)

        requirements_data = {"product_names": remaining_product_names, "requirements": requirements}
        return requirements_data

    def download_comments(self, resolved_requirements_data):
        n_requirements = len(resolved_requirements_data["requirements"])
        _logger.info("Fetching all comments for {} requirements...".format(n_requirements))
        bugzilla_fetcher = bugzillafetcher.BugzillaFetcher("{}/{}".format(self._base_url, "bug"))
        max_http_repeat = 10
        counter = 0
        for (requirement_id, requirement) in resolved_requirements_data["requirements"].items():
            if requirement.number_of_comments is not None and requirement.number_of_comments > 0:
                print("Skipping {}".format(requirement_id))
                counter += 1
                continue

            _logger.info("Progress: {:.1%}".format(float(counter) / float(n_requirements)))
            n_repeat = 0
            while n_repeat < max_http_repeat:
                try:
                    requirement.comments = bugzilla_fetcher.fetch_comments(requirement_id)
                    requirement.number_of_comments = len(requirement.comments)
                    resolved_requirements_data["requirements"][requirement_id] = requirement
                    _logger.info("  Number of fetched comments for #{}: {}".format(requirement_id, len(requirement.comments)))
                    import pickle
                    pickle.dump(resolved_requirements_data, open(self._dataset_file_path, "wb"))
                    #time.sleep(0.1)
                    counter += 1
                    break
                except Exception as e:
                    wait_time_in_seconds = math.pow(2, n_repeat)
                    _logger.error("    {}".format(traceback.format_exc()))
                    _logger.info("    Request(s) failed... Try again in {} seconds...".format(wait_time_in_seconds))
                    time.sleep(wait_time_in_seconds)
                    n_repeat += 1
                    continue

        return resolved_requirements_data

    def _fetch_bugs_of_product_and_component(self, n, product_name, status, component_name, limit, offset):
        max_http_repeat = 10
        n_repeat = 0
        while n_repeat < max_http_repeat:
            try:
                return self.download_bugs_of_product_of_last_n_years(self._base_url, n, product_name, status,
                                                                     component_name, limit=limit, offset=offset)
            except Exception as e:
                wait_time_in_seconds = math.pow(2, n_repeat)
                _logger.error("    {}".format(traceback.format_exc()))
                _logger.info("    Request(s) failed... Try again in {} seconds...".format(wait_time_in_seconds))
                time.sleep(wait_time_in_seconds)
                n_repeat += 1
                continue

    def download_bugs_of_product_of_last_n_years(self, base_url, n: int=3, product_name: str=None, status: str=None,
                                                 component: str=None, limit: int=None, offset: int=None) -> [bugzillafetcher.Bug]:
        creation_time = datetime.datetime.now() - datetime.timedelta(days=n * 365)
        creation_time_value = creation_time.strftime("%Y-%m-%d")
        parameters = [('creation_time', creation_time_value)]

        if status is not None:
            parameters += [('status', status)]

        if limit is not None:
            parameters += [('limit', limit)]

        if offset is not None:
            parameters += [('offset', offset)]

        parameters += [('product', product_name)]

        if component is not None:
            parameters += [('component', component)]

        url = "{}/bug?{}".format(base_url, urllib.parse.urlencode(parameters))
        _logger.info("    Fetching bugs for product='{}' and component='{}' from: {}".format(product_name, component, url))
        r = requests.get(url, headers=HEADERS)
        r.raise_for_status()
        parsed_data = r.json()
        bugs_data = parsed_data["bugs"]
        new_bugs_data = []
        for bd in bugs_data:
            new_bd = bd
            for field in bugzillafetcher.bug_fields:
                if field not in set(new_bd.keys()):
                    new_bd[field] = None
            new_bugs_data += [new_bd]
        if self._dataset_name == "libreoffice":
            bugzillafetcher.Bug = namedtuple('Bug', bugzillafetcher.bug_fields + ['cf_crashreport'])
        elif self._dataset_name == "mozilla":
            all_bug_fields = bugzillafetcher.bug_fields + [
                'cf_user_story', 'cf_qa_whiteboard', 'cf_fx_iteration', 'cf_last_resolved', 'type', 'comment_count',
                'regressions', 'mentors', 'mentors_detail', 'votes', 'cf_fx_points', 'regressed_by', 'duplicates'
            ]
            bugzillafetcher.Bug = namedtuple('Bug', all_bug_fields)
            bugs_data = []
            removed_keys = set()
            for d in new_bugs_data:
                bug_data = {}
                for k in d.keys():
                    if k in all_bug_fields:
                        bug_data[k] = d[k]
                    else:
                        removed_keys.add(k)
                bugs_data += [bug_data]
            new_bugs_data = bugs_data
        return list(map(lambda d: bugzillafetcher.Bug(**d), new_bugs_data))
