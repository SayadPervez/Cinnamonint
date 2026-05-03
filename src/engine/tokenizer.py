"""
Token identification — find known tokens in a sentence.
"""

import re


def _strip_punctuation(word):
    """strip leading/trailing punctuation from a word for keyword lookup."""
    return word.strip(".,;:!?\"'()[]{}")


def find_tokens_in_sentence(sentence, keyword_map):
    """find all known tokens present in the sentence.

    returns a list of dicts:
        [{"keyword": <str>, "position": <int>, "token": <token_dict>}, ...]

    each keyword is matched as a whole word (not a substring).
    matches are returned sorted by position in the sentence.
    """
    words = sentence.lower().split()
    found = []
    seen_keywords = set()

    # single-word tokens — match against individual words
    for i, word in enumerate(words):
        cleaned = _strip_punctuation(word)
        if cleaned in keyword_map and cleaned not in seen_keywords:
            position = _word_position(sentence, words, i)
            found.append({
                "keyword": cleaned,
                "position": position,
                "token": keyword_map[cleaned],
            })
            seen_keywords.add(cleaned)

    # multi-word tokens — scan for phrases in the sentence
    for keyword, token in keyword_map.items():
        if " " in keyword and keyword not in seen_keywords:
            pattern = r"\b" + re.escape(keyword) + r"\b"
            match = re.search(pattern, sentence.lower())
            if match:
                found.append({
                    "keyword": keyword,
                    "position": match.start(),
                    "token": token,
                })
                seen_keywords.add(keyword)

    found.sort(key=lambda x: x["position"])
    return found


def find_token_boundary(text, exclude_keywords=None):
    """find the character position of the first known token in text.

    batch-checks all words in the text against the registry in a single query.
    scalable: one DB query regardless of token count.

    args:
        text:             the text to scan for token boundaries
        exclude_keywords: keyword(s) to skip (the handler's own keyword).
                          accepts a string or a set of strings.

    returns:
        character position of the first other token found,
        or len(text) if no boundary is found.
    """
    from src.registry.store import get_keywords_for_words

    if exclude_keywords is None:
        exclude_keywords = set()
    elif isinstance(exclude_keywords, str):
        exclude_keywords = {exclude_keywords}

    lower = text.lower()
    words = lower.split()

    # single DB query — get all matching keywords for these words
    keyword_map = get_keywords_for_words(words)

    pos = 0
    for word in words:
        word_start = lower.find(word, pos)
        cleaned = _strip_punctuation(word)
        if cleaned in exclude_keywords:
            pos = word_start + len(word)
            continue
        if cleaned in keyword_map:
            return word_start
        pos = word_start + len(word)

    return len(text)


def find_token_boundary_reverse(text, exclude_keywords=None):
    """find the character position AFTER the last known token in text.

    scans text for tokens and returns the position just after the last one
    found. this marks where the operand territory for a subsequent handler
    begins (i.e., numbers after this position belong to the handler on the
    right, not the token on the left).

    args:
        text:             the text to scan
        exclude_keywords: keyword(s) to skip

    returns:
        character position after the last token found,
        or 0 if no token is found (entire text is available).
    """
    from src.registry.store import get_keywords_for_words

    if exclude_keywords is None:
        exclude_keywords = set()
    elif isinstance(exclude_keywords, str):
        exclude_keywords = {exclude_keywords}

    lower = text.lower()
    words = lower.split()

    keyword_map = get_keywords_for_words(words)

    last_boundary = 0
    pos = 0
    for word in words:
        word_start = lower.find(word, pos)
        cleaned = _strip_punctuation(word)
        if cleaned in exclude_keywords:
            pos = word_start + len(word)
            continue
        if cleaned in keyword_map:
            last_boundary = word_start + len(word)
        pos = word_start + len(word)

    return last_boundary


def _word_position(sentence, words, word_index):
    """find the character position of the word at word_index in the sentence."""
    lower = sentence.lower()
    pos = 0
    for i, word in enumerate(words):
        idx = lower.find(word, pos)
        if i == word_index:
            return idx
        pos = idx + len(word)
    return 0
