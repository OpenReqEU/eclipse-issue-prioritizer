# -*- coding: utf-8 -*-

import re
import logging
import unicodedata


_logger = logging.getLogger(__name__)
tokens_punctuation_re = re.compile(r"(\.|,|'|-|!|:|;|\"|\?|/|\(|\)|~)$")
single_character_tokens_re = re.compile(r"^\W$")


def key_words_for_tokenization(all_requirement_titles):
    '''
        Collects important words that must NOT be destroyed by tokenization and filtering process.
    '''
    tokens_of_requirements = map(lambda t: unicodedata.normalize('NFKD', t.lower().replace('-', ' ')).encode('ascii', 'ignore').split(), all_requirement_titles)
    all_tokens = [t for requirement_tokens in tokens_of_requirements for t in requirement_tokens]
    return list(set(all_tokens))


def tokenize_requirements(requirements, important_key_words, lang="en"):
    """

        Customized tokenizer for our special needs.
        Unfortunately, many tokenizers out there are not aware of technical terms like C#, C++,
        asp.net, etc.

        Instead we could have used an existing tokenizer tool and:
         a) modify/adapt the tokenization-rules
         b) or use classification to train them
        but this would have had several drawbacks for us:
         a) the tokenizer would be still not flexible enough for our needs...
         b) we would have had to create much training data...

        Thus, we decided to come up with our own flexible tokenizer solution that is custom-designed
        to tokenize StackExchange posts efficiently.

        NOTE: In order to ensure that our tokenizer is working correct, we have created many
              unit-testcases for this python-module (see: "tests"-folder of this project)

    """
    _logger.info("Tokenizing requirements")
    assert(isinstance(requirements, list))
    assert(isinstance(important_key_words, list))
    sorted_important_key_words_to_keep = sorted(important_key_words, reverse=True)

    regex_str = [
        r"(?:[a-z][a-z'\-\.]+[a-z])",      # words containing "'", "-" or "."
        r'\w+\&\w+',                       # e.g. AT&T
        r'(?:@[\w_]+)',                    # @-mentions
        r"(?:\#+[\w_]+[\w\'_\-]*[\w_]+)",  # hash-tags
        # r'(?:\d+\%)',                    # percentage
        r'(?:(?:\d+,?)+(?:\.?\d+)?)',      # numbers
        r'(?:[\w_]+)',                     # other words
        r'(?:\S)'                          # anything else
    ]
    tokens_ignore_re = re.compile(r'(' + '|'.join(regex_str) + ')', re.VERBOSE | re.IGNORECASE)

    # regex to split/tokenize by key words
    regex_str = map(lambda word: '\s' + re.escape(str(word)) + '\W', sorted_important_key_words_to_keep)
    split_important_words_re = re.compile(r'(' + '|'.join(regex_str) + ')', re.VERBOSE | re.IGNORECASE)
    last_char_is_no_alphanum_re = re.compile(r'(\W)', re.VERBOSE | re.IGNORECASE)

    def _tokenize_text(s, sorted_important_words_to_keep, split_important_words_re, lang="en"):
        def _pre_tokenize_important_words(chunks, sorted_important_words_to_keep, split_important_words_re):
            """
                Only looks and tokenizes for important words.
                The rest remains untokenized.
            """
            assert(len(sorted_important_words_to_keep) > 0)
            new_chunks = []
            for chunk in chunks:
                assert(isinstance(chunk, str))
                # case: chunk is a tag (i.e. chunk == tag_X)
                if chunk.strip() in sorted_important_words_to_keep:
                    new_chunks.append(chunk)
                    continue

                if chunk.strip()[:-1] in sorted_important_words_to_keep \
                and len(last_char_is_no_alphanum_re.findall(chunk.strip()[-1])) == 1:
                    new_chunks.append(chunk.strip()[:-1])
                    continue

                # case: chunk is not a tag
                # check if chunk contains (!) tag (i.e. tag_X is part of chunk!)
                sub_chunks = [chunk]
                sub_parts = split_important_words_re.split(chunk)
                if len(sub_parts) > 1:
                    sub_parts = filter(lambda ch: len(ch.strip()) > 0, sub_parts)
                    sub_parts = map(lambda ch: ' '+ ch.strip() + ' ', sub_parts)
                    sub_chunks = _pre_tokenize_important_words(sub_parts, sorted_important_words_to_keep, split_important_words_re)
                    sub_chunks = map(lambda ch: ch.strip(), sub_chunks)
                    sub_chunks = filter(lambda ch: len(ch) > 0, sub_chunks)
                new_chunks += sub_chunks
            return new_chunks


        def tokenize(s, sorted_important_words_to_keep, split_important_words_re):
            if len(sorted_important_words_to_keep) > 0:
                # tokenize important words first!
                tokens = _pre_tokenize_important_words([' %s ' % s], sorted_important_words_to_keep, split_important_words_re)
                tokens = map(lambda t: t.strip(), tokens)
            else:
                tokens = [s.strip()]

            # now tokenize all other words!
            final_tokens = []
            for token in tokens:
                assert(isinstance(token, str))
                # case: token is an important word (i.e. already tokenized) -> do no further tokenization!
                if token in sorted_important_words_to_keep:
                    final_tokens.append(token)
                    continue

                # case: token is not part of the important word list and even does not contain
                #       any word from the important word list. This token can be a single word
                #       or multiple words that are part of a sentence
                #       -> further tokenization required
                final_tokens += tokens_ignore_re.findall(' %s ' % token)
            return final_tokens


        def remove_all_tailing_punctuation_characters(token):
            old_token = token
            while True:
                if len(tokens_punctuation_re.findall(token)) == 0:
                    if len(old_token) >= 2 and old_token != token:
                        _logger.debug("Replaced: %s -> %s" % (old_token, token))
                    return token
                token = token[:-1]


        # pre- and append single whitespace character before and at the end of the string
        # This really makes the regular expressions a bit less complex
        if lang == "en":
            s = s.replace("'s", "")
        s = " {} ".format(s.lower()) # also lower case all letters

        # remove unicode characters
        s = unicodedata.normalize("NFKD", s).encode('ascii', 'ignore').decode("utf-8")

        # manually replace those emoticons/smilies not handled by regex:
        s = str(s)
        s = s.replace(":d", "")
        s = s.replace(':p', '')
        s = s.replace(':-d', '')
        s = s.replace(':-p', '')

        # split words by '_'
        s = " ".join(s.split("_"))

        # tokenize
        tokens = tokenize(s, sorted_important_words_to_keep, split_important_words_re)

        # remove whitespaces before and after
        tokens = map(lambda t: t.strip(), tokens)

        # remove tailing punctuation characters (if present)
        tokens = map(remove_all_tailing_punctuation_characters, tokens)

        # finally remove empty tokens
        return list(filter(lambda t: len(t) > 0, tokens))

    for r in requirements:
        r.summary_tokens = _tokenize_text(r.summary, sorted_important_key_words_to_keep, split_important_words_re, lang=lang)

