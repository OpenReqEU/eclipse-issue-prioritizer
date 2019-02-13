# -*- coding: utf-8 -*-

import nltk
import os
import logging
from application.util import helper
from nltk.corpus import stopwords


_logger = logging.getLogger(__name__)
nltk.data.path = [os.path.join(helper.APP_PATH, "corpora", "nltk_data")]


def remove_stopwords(requirements, lang="en"):
    _logger.info("Removing stop-words from requirement' tokens")
    stop_words_file_path = os.path.join(helper.DATA_PATH, 'stopwords')
    data_set_stop_words = set()
    if os.path.isfile(stop_words_file_path):
        with open(stop_words_file_path, 'r') as f:
            for line in f:
                data_set_stop_words.add(line.strip())

    if lang == "en":
        stop_words = set(stopwords.words('english') + list(data_set_stop_words))
    elif lang == "de":
        stop_words = set(stopwords.words('german') + list(data_set_stop_words))
    else:
        stop_words = data_set_stop_words

    for r in requirements:
        r.summary_tokens = list(filter(lambda t: t not in stop_words, r.summary_tokens))

