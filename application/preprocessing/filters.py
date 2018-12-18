# -*- coding: utf-8 -*-

import logging
import re
import os
from application.util import helper


_logger = logging.getLogger(__name__)
emoticons_data_file = os.path.join(helper.APP_PATH, "corpora", "emoticons", "emoticons")
tokens_punctuation_re = re.compile(r"(\.|!|\?|\(|\)|~)$")


def filter_tokens(requirements, important_key_words):
    _logger.info("Filter posts' tokens")

    def _is_number(current_token):
        return helper.is_int_or_float(current_token) or all(helper.is_int_or_float(x) for x in re.split('\.|,|-|rc', current_token))

    def _is_version_number(previous_token, current_token):
        return _is_number(current_token) and previous_token in {
            "eclipse", "junit", "sdk", "jdk", "java", "cdt", "emf", "macos", "oaw", "wtp",
            "jst", "geronimo", "wls", "tomcat", "websphere", "ce", "version",
            "pocketpc", "port", "line", "ajp", "ie", "oc4j", "release", "vers"
        }

    special_characters = "!#$%&'()*+,-./:;<=>?@[\]^_`{|}~"
    special_characters_set = set(map(lambda c: c, special_characters))

    def _filter_tokens(tokens, important_key_words):
        # make sure that all tokens do not contain any whitespaces before and at the end
        tokens = map(lambda t: t.strip(), tokens)
        tokens = map(lambda t: t.strip("."), tokens)

        # remove special characters
        tokens = filter(lambda t: t not in special_characters_set, tokens)

        # remove "@"-mentions and twitter hashtags
        tokens = list(filter(lambda t: not t.startswith("@") and not t.startswith("#"), tokens))

        # consider version numbers but remove plain numbers
        previous_tokens = tokens[:]
        tokens = map(lambda tup: tup[1], filter(lambda tup: not _is_number(tup[1]) or _is_version_number((previous_tokens[tup[0] - 1] if tup[0] > 0 else ""), tup[1]), enumerate(tokens)))

        tokens = list(tokens)[:]
        new_tokens = []
        omit_next_token = False
        for idx, t in enumerate(tokens):
            if omit_next_token is True:
                omit_next_token = False
                continue

            next_token = tokens[idx + 1] if (idx + 1) < len(tokens) else ""
            if _is_version_number(t, next_token):
                new_tokens += [t + " " + next_token]
                omit_next_token = True
                continue

            new_tokens += [t]

        # remove single-character and empty tokens
        tokens = filter(lambda t: len(t) > 1 or t in important_key_words, new_tokens)

        # remove empty tokens
        return list(filter(lambda t: len(t) > 0, tokens))

    for r in requirements:
        r.summary_tokens = _filter_tokens(r.summary_tokens, important_key_words)

