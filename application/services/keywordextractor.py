# coding: utf-8

from typing import List  # noqa: F401
from application.models.requirement import Requirement
from application.util import helper
from application.preprocessing import filters
from application.preprocessing import stopwords
from application.preprocessing import pos
from application.preprocessing import lemmatizer
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
            r.summary = r.summary.lower()

    def _replace_german_umlauts(self, requirements):
        _logger.info("Replace umlauts")
        for r in requirements:
            assert (isinstance(r, Requirement))
            r.summary = helper.replace_german_umlaut(r.summary)

    def _remove_german_abbreviations(self, requirements):
        _logger.info("Remove abbreviations")
        for r in requirements:
            assert (isinstance(r, Requirement))
            r.summary = r.summary.replace('z.b.', '')

    def _remove_english_abbreviations(self, requirements):
        _logger.info("Remove abbreviations")
        for r in requirements:
            assert (isinstance(r, Requirement))
            r.summary = r.summary.replace('e.g.', '')
            r.summary = r.summary.replace('i.e.', '')
            r.summary = r.summary.replace('in order to', '')

    def extract_keywords(self, requirements: List[Requirement], enable_pos_tagging=False, enable_lemmatization=False,
                         lang="en") -> Requirement:
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

        for r in requirements:
            # remove links
            r.summary = re.sub(r'^https?:\/\/.*[\r\n]*', "", r.summary, flags=re.MULTILINE)
            r.summary = re.sub(r'^ftps?:\/\/.*[\r\n]*', "", r.summary, flags=re.MULTILINE)

            # remove special characters
            for special_character in {"!", ",", "?", ":", ";", "&", "(", ")", "_", "[", "]", "{", "}", "'",
                                      "\"", "“", "'s", "=>", "->", "->>", "<<->>", "%20", "==", "/", "<", ">", "\\"}:
                r.summary = r.summary.replace(special_character, " ")

            # tokenize
            r.summary_tokens = r.summary.split()

        #tokenizer.tokenize_requirements(requirements, important_key_words, lang=lang)
        n_tokens = sum(map(lambda r: len(list(r.summary_tokens)), requirements))
        filters.filter_tokens(requirements, ['c'])
        stopwords.remove_stopwords(requirements, lang=lang)

        #extracted_key_words = tokenizer.key_words_for_tokenization(all_requirement_summaries)
        extracted_unique_key_words = list(set([t for r in requirements for t in r.summary_tokens]))
        _logger.info("Number of extracted key words {} (altogether)".format(len(extracted_unique_key_words)))

        # -----------------------------------------------------------------------------------------------
        # NOTE: Both NLTK and Stanford POS-tagging is not working as good as expected, because we are
        #       getting a lot of wrong tags (e.g. NN instead of VB).
        #       -> Outlook: use unsupervised POS-tagging (very time consuming to
        #                   manually label enough training data...)
        # -----------------------------------------------------------------------------------------------
        if enable_pos_tagging is True:
            _logger.warning("POS Tagging enabled!")
            pos.pos_tagging(requirements, lang=lang)

        # -----------------------------------------------------------------------------------------------
        # NOTE: it does not makes sense to use both lemmatization
        #       lemmatizer also requires pos_tagging beforehand!
        # -----------------------------------------------------------------------------------------------
        if enable_lemmatization is True:
            _logger.warning("Lemmatization enabled!")
            lemmatizer.word_net_lemmatizer(requirements, lang=lang)

        n_filtered_tokens = n_tokens - sum(map(lambda t: len(list(t.summary_tokens)), requirements))
        if n_tokens > 0:
            p_filtered_tokens = round(float(n_filtered_tokens) / n_tokens * 100.02)
            _logger.info("Removed {} ({}%) of {} tokens (altogether)".format(n_filtered_tokens, p_filtered_tokens, n_tokens))

        return extracted_unique_key_words
