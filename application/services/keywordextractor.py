# coding: utf-8

from typing import List  # noqa: F401
from application.models.requirement import Requirement
from application.util import helper
from application.preprocessing import filters
from application.preprocessing import stopwords
import logging
import re


_logger = logging.getLogger(__name__)


class KeywordExtractor(object):

    def __init__(self):
        pass

    def _to_lower_case(self, requirements):
        _logger.info("Lower case requirements title and description")
        for r in requirements:
            assert (isinstance(r, Requirement))
            r.new_summary = r.new_summary.lower()

    def _replace_german_umlauts(self, requirements):
        _logger.info("Replace umlauts")
        for r in requirements:
            assert (isinstance(r, Requirement))
            r.new_summary = helper.replace_german_umlaut(r.new_summary)

    def _remove_german_abbreviations(self, requirements):
        _logger.info("Remove abbreviations")
        for r in requirements:
            assert (isinstance(r, Requirement))
            r.new_summary = r.new_summary.replace('z.b.', '')

    def _remove_english_abbreviations(self, requirements):
        _logger.info("Remove abbreviations")
        for r in requirements:
            assert (isinstance(r, Requirement))
            r.new_summary = r.new_summary.replace('e.g.', '')
            r.new_summary = r.new_summary.replace('i.e.', '')
            r.new_summary = r.new_summary.replace('in order to', '')

    def extract_keywords(self, requirements: List[Requirement], lang="en") -> List[str]:
        _logger.info("Preprocessing bugs")
        assert(isinstance(requirements, list))
        if len(requirements) == 0:
            return []

        self._to_lower_case(requirements)
        if lang == "de":
            self._replace_german_umlauts(requirements)
            self._remove_german_abbreviations(requirements)
        elif lang == "en":
            self._remove_english_abbreviations(requirements)

        multitokens = set()
        for r in requirements:
            multitoken_pattern = re.search(r'^\[([a-zA-Z])+\s([a-zA-Z])+\]*', r.new_summary)
            if multitoken_pattern is not None:
                multitokens.add(multitoken_pattern.group().replace("[", "").replace("]", ""))

            # remove links
            r.new_summary = re.sub(r'^https?:\/\/.*[\r\n]*', "", r.new_summary, flags=re.MULTILINE)
            r.new_summary = re.sub(r'^ftps?:\/\/.*[\r\n]*', "", r.new_summary, flags=re.MULTILINE)

            # remove special characters
            for special_character in {"!", ",", "?", ":", ";", "&", "(", ")", "_", "[", "]", "{", "}", "'",
                                      "\"", "“", "'s", "=>", "->", "->>", "<<->>", "%20", "==", "/", "<", ">", "\\"}:
                r.new_summary = r.new_summary.replace(special_character, " ")

            # tokenize
            r.summary_tokens = r.new_summary.split()

        #tokenizer.tokenize_requirements(requirements, important_key_words, lang=lang)
        n_tokens = sum(map(lambda r: len(list(r.summary_tokens)), requirements))
        filters.filter_tokens(requirements, multitokens, ["c"])

        # replace synonyms
        for r in requirements:
            for old_word, new_word in [("deletion", "delete"), ("test", "tests"), ("method", "methods"),
                                       ("styling", "styles"), ("style", "styles"), ("checking", "checks"),
                                       ("check", "checks"), ("configurations", "configuration"), ("task", "tasks"),
                                       ("assertion", "assert"), ("dialog", "dialogs"), ("fixes", "fix"),
                                       ("building", "builds"), ("build", "builds"), ("persist", "persistence"),
                                       ("persists", "persistence"), ("persisting", "persistence"),
                                       ("persisted", "persistence"), ("clazz", "class"), ("classes", "class"),
                                       ("event", "events"), ("script", "scripts"), ("adding", "add"), ("ids", "id"),
                                       ("log", "logs"), ("logging", "logs"), ("calculation", "calculate"),
                                       ("reading", "read"), ("reads", "read"), ("constant", "constants"),
                                       ("dependency", "dependencies"), ("todo", "todos"), ("user interface", "ui"),
                                       ("java7", "java 7"), ("java8", "java 8")]:
                r.summary_tokens = list(map(lambda t: new_word if t == old_word else t, r.summary_tokens))

        stopwords.remove_stopwords(requirements)

        #extracted_key_words = tokenizer.key_words_for_tokenization(all_requirement_summaries)
        extracted_unique_key_words = list(set([t for r in requirements for t in r.summary_tokens]))
        _logger.info("Number of extracted key words {} (altogether)".format(len(extracted_unique_key_words)))

        n_filtered_tokens = n_tokens - sum(map(lambda t: len(list(t.summary_tokens)), requirements))
        if n_tokens > 0:
            p_filtered_tokens = round(float(n_filtered_tokens) / n_tokens * 100.02)
            _logger.info("Removed {} ({}%) of {} tokens (altogether)".format(n_filtered_tokens,
                                                                             p_filtered_tokens, n_tokens))

        return extracted_unique_key_words
