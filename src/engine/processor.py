"""
The iterative reduction engine — core sentence processing loop.
"""

import time

from src.engine.tokenizer import find_tokens_in_sentence
from src.engine.resolver import resolve_next_token
from src.registry.loader import load_handler
from src.registry.store import get_all_keywords, get_keywords_for_words
from src.config.settings import (
    SOFT_ITERATION_LIMIT,
    WARN_ITERATION_LIMIT,
    HARD_ITERATION_LIMIT,
    WORD_LOOKUP_THRESHOLD,
)


def process(sentence, on_iteration=None, on_limit_reached=None):
    """run the iterative reduction loop on a sentence.

    parameters:
        sentence          — the raw input string
        on_iteration      — optional callback(iteration_num, before, keyword,
                            handler_path, after, duration_ms) called after each
                            iteration for logging
        on_limit_reached  — optional callback(iteration_count, current_sentence)
                            that returns True to continue or False to stop.
                            used for the 50-iteration pause-and-ask feature.

    returns:
        (final_sentence, iteration_count, status)
        status is one of: 'ok', 'limit_reached', 'error'
    """
    keyword_map = _build_keyword_map(sentence)
    iteration = 0
    status = "ok"

    while True:
        # --- find tokens in current sentence ---
        found = find_tokens_in_sentence(sentence, keyword_map)
        if not found:
            break

        # --- check iteration limits ---
        if iteration >= HARD_ITERATION_LIMIT:
            status = "limit_reached"
            break

        if iteration > 0 and iteration % SOFT_ITERATION_LIMIT == 0:
            if on_limit_reached:
                should_continue = on_limit_reached(iteration, sentence)
                if not should_continue:
                    status = "limit_reached"
                    break
            if iteration >= WARN_ITERATION_LIMIT and on_limit_reached:
                # the callback already handled it above
                pass

        # --- pick the next token to process ---
        chosen = resolve_next_token(found)
        if chosen is None:
            break

        keyword = chosen["keyword"]
        token = chosen["token"]
        handler_path = token["handler_path"]

        # --- load and execute handler ---
        before = sentence
        start_time = time.perf_counter_ns()

        try:
            handler = load_handler(handler_path)
            sentence = handler(sentence)
        except Exception as e:
            # handler crashed — stop processing, report error
            if on_iteration:
                on_iteration(iteration + 1, before, keyword, handler_path,
                             f"ERROR: {e}", 0)
            status = "error"
            break

        elapsed_ms = (time.perf_counter_ns() - start_time) // 1_000_000
        iteration += 1

        # --- clean up whitespace ---
        sentence = _normalize_whitespace(sentence)

        # --- detect stall: handler returned sentence unchanged ---
        if sentence == _normalize_whitespace(before):
            # handler couldn't process the token (e.g. no valid operands)
            # log the no-op iteration and stop to avoid infinite loop
            if on_iteration:
                on_iteration(iteration, before, keyword, handler_path,
                             sentence, elapsed_ms)
            break

        # --- log the iteration ---
        if on_iteration:
            on_iteration(iteration, before, keyword, handler_path,
                         sentence, elapsed_ms)

        # --- refresh keyword map (sentence may have changed) ---
        keyword_map = _build_keyword_map(sentence)

    return sentence, iteration, status


def _build_keyword_map(sentence):
    """build the keyword map for a sentence.

    for short sentences (≤ WORD_LOOKUP_THRESHOLD words), look up only the
    words present in the sentence — O(words) indexed DB lookups.
    for long sentences, fall back to fetching all keywords.
    """
    words = sentence.lower().split()
    if len(words) <= WORD_LOOKUP_THRESHOLD:
        return get_keywords_for_words(words)
    return get_all_keywords()


def _normalize_whitespace(s):
    """collapse multiple spaces into one and strip leading/trailing space."""
    return " ".join(s.split())
