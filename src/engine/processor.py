"""
The iterative reduction engine — core sentence processing loop.
"""

import time

from src.engine.tokenizer import find_tokens_in_sentence, _strip_punctuation
from src.engine.resolver import resolve_next_token
from src.registry.loader import execute_handler
from src.registry.store import get_all_keywords, get_keywords_for_words
from src.safety.approvals import check_and_approve
from src.safety.limits import check_iteration_limit
from src.config.settings import WORD_LOOKUP_THRESHOLD, HANDLER_TIMEOUT_SECONDS


# handlers that manage their own timing (e.g. wait/pause with countdowns)
# are exempt from the subprocess timeout.
_TIMEOUT_EXEMPT_HANDLERS = {"tokens/utility/wait.py"}

# handlers whose print output should stream live to the terminal
# (stderr inherited, not buffered)
_LIVE_OUTPUT_HANDLERS = {"tokens/utility/wait.py"}


def process(sentence, on_iteration=None, on_limit_reached=None,
            interactive=True):
    """run the iterative reduction loop on a sentence.

    parameters:
        sentence          — the raw input string
        on_iteration      — optional callback(iteration_num, before, keyword,
                            handler_path, after, duration_ms) called after each
                            iteration for logging
        on_limit_reached  — optional callback(iteration_count, current_sentence)
                            that returns True to continue or False to stop.
                            used for the 50-iteration pause-and-ask feature.
        interactive       — whether approval prompts can be shown (False for
                            piped input)

    returns:
        (final_sentence, iteration_count, status)
        status is one of: 'ok', 'limit_reached', 'error'
    """
    keyword_map = _build_keyword_map(sentence)
    iteration = 0
    status = "ok"
    skipped_keywords = set()

    while True:
        # --- find tokens in current sentence ---
        found = find_tokens_in_sentence(sentence, keyword_map)
        # filter out keywords that have already stalled on this sentence
        candidates = [f for f in found if f["keyword"] not in skipped_keywords]
        if not candidates:
            break

        # --- check iteration limits ---
        should_continue, limit_status = check_iteration_limit(
            iteration, sentence, on_limit_reached
        )
        if not should_continue:
            status = limit_status
            break

        # --- pick the next token to process ---
        chosen = resolve_next_token(candidates)
        if chosen is None:
            break

        keyword = chosen["keyword"]
        token = chosen["token"]
        handler_path = token["handler_path"]

        # --- approval gate (flagged tokens only) ---
        if not check_and_approve(token, sentence, interactive=interactive):
            skipped_keywords.add(keyword)
            continue

        # --- load and execute handler ---
        before = sentence
        start_time = time.perf_counter_ns()

        try:
            timeout = None if handler_path in _TIMEOUT_EXEMPT_HANDLERS else HANDLER_TIMEOUT_SECONDS
            inherit_stderr = handler_path in _LIVE_OUTPUT_HANDLERS
            sentence = execute_handler(handler_path, sentence, timeout=timeout,
                                       inherit_stderr=inherit_stderr)
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
            # handler couldn't process the token — skip it and try next
            skipped_keywords.add(keyword)
            if on_iteration:
                on_iteration(iteration, before, keyword, handler_path,
                             sentence, elapsed_ms)
            continue

        # --- handler made progress — reset skipped set ---
        skipped_keywords.clear()

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
    cleaned = [_strip_punctuation(w) for w in words]
    cleaned = [w for w in cleaned if w]
    if len(words) <= WORD_LOOKUP_THRESHOLD:
        return get_keywords_for_words(cleaned)
    return get_all_keywords()


def _normalize_whitespace(s):
    """collapse multiple spaces into one and strip leading/trailing space."""
    return " ".join(s.split())
