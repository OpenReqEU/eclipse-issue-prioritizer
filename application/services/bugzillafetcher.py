import requests
from requests_futures.sessions import FuturesSession
from concurrent.futures import wait
import urllib.parse
from typing import List  # noqa: F401
import datetime
from collections import namedtuple


bug_fields = [
    'id',
    'is_open',
    'summary',
    'version',
    'depends_on',
    'is_cc_accessible',
    'severity',
    'groups',
    'resolution',
    'creation_time',
    'qa_contact',
    'last_change_time',
    'dupe_of',
    'assigned_to',
    'cc_detail',
    'op_sys',
    'alias',
    'flags',
    'target_milestone',
    'see_also',
    'url',
    'is_confirmed',
    'assigned_to_detail',
    'deadline',
    'is_creator_accessible',
    'component',
    'priority',
    'creator',
    'classification',
    'status',
    'platform',
    'creator_detail',
    'keywords',
    'blocks',
    'product',
    'whiteboard',
    'cc',
    'qa_contact_detail'
]

comment_fields = [
    'attachment_id',
    'bug_id',
    'count',
    'creation_time',
    'creator',
    'id',
    'is_private',
    'raw_text',
    'tags',
    'text',
    'time'
]

Bug = namedtuple('Bug', bug_fields)
Comment = namedtuple('Comment', comment_fields)


class BugzillaFetcher(object):

    def __init__(self, base_url: str):
        self._base_url = base_url

    def fetch_bugs(self, assignee_mail_address: str, products: List[str], components: List[str],
                   status: str=None, limit: int=0, max_age_years: int=7) -> [Bug]:
        last_change_time = datetime.datetime.now() - datetime.timedelta(days=2 * 365)
        last_change_time_value = last_change_time.strftime("%Y-%m-%d")
        creation_time = datetime.datetime.now() - datetime.timedelta(days=max_age_years * 365)
        creation_time_value = creation_time.strftime("%Y-%m-%d")
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36",
            "Accept": "application/json"
        }

        parameters = [
            ('creation_time', creation_time_value),
            ('last_change_time', last_change_time_value)
        ]

        #if limit > 0:
        #    parameters += [('limit', limit)]

        if assignee_mail_address is not None:
            parameters += [('assigned_to', assignee_mail_address)]

        if status is not None:
            parameters += [('status', status)]

        parameters += map(lambda product: ("product", product), products)
        parameters += map(lambda component: ("component", component), components)

        url = self._base_url + "?" + urllib.parse.urlencode(parameters)
        print("Fetching bugs from: {}".format(url))
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        print(r.headers)
        print(r.status_code == requests.codes.ok)
        parsed_data = r.json()
        bugs_data = parsed_data["bugs"]
        new_bugs_data = []
        for bd in bugs_data:
            new_bd = bd
            for field in bug_fields:
                if field not in set(new_bd.keys()):
                    new_bd[field] = None
            new_bugs_data += [new_bd]
        return list(map(lambda d: Bug(**d), new_bugs_data))

    def fetch_comments(self, bug_id: int) -> [Comment]:
        url = "{}/{}/comment".format(self._base_url, bug_id)
        print("Fetching comments from: {}".format(url))
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36",
            "Accept": "application/json"
        }
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        print(r.headers)
        print(r.status_code == requests.codes.ok)
        parsed_data = r.json()
        comments_data = parsed_data["bugs"][str(bug_id)]["comments"]
        comments = list(map(lambda d: Comment(**d), comments_data))
        return comments

    def fetch_comments_parallelly(self, bug_ids: List[int]) -> [Comment]:
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36",
            "Accept": "application/json"
        }

        def exception_handler(request, exception):
            print("ERROR: An exception occurred! {}".format(exception))

        urls = list(map(lambda bug_id: "{}/{}/comment".format(self._base_url, bug_id), bug_ids))
        session = FuturesSession(max_workers=len(urls))
        futures = [session.get(u, headers=headers) for u in urls]
        done, incomplete = wait(futures)
        session.close()
        #print(done)
        #print(incomplete)

        if len(incomplete) > 0:
            print("ERROR!!! Failed to process at least one request...")

        bug_comments = {}
        for f in done:
            r = f.result()
            parsed_data = r.json()
            bugs_data = parsed_data["bugs"]
            included_bug_ids = list(bugs_data.keys())
            assert(len(included_bug_ids) == 1)
            bug_id = included_bug_ids[0]
            bug_comments[int(bug_id)] = bugs_data[bug_id]["comments"]
        return bug_comments
