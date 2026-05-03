"""
Pre-processing spell correction for the reduction engine.

Runs before the reduction loop. Checks each word in the input against
registered tokens/aliases and (optionally) a bundled English dictionary.
Suggests corrections interactively — never silently autocorrects.

Two modes (determined by presence of data/words.txt):
  - Token-only: suggest corrections only against tokens/aliases
  - Full: skip known English words, flag truly unknown words
"""

import difflib
import os
import readline
import re

from rich.console import Console

from src.config import settings
from src.registry.store import get_all_keywords
from src.engine.user_dictionary import (
    load_user_words, add_word, load_corrections, add_correction,
)

console = Console()

# module-level caches (loaded once per session)
_english_words = None
_dictionary_available = None


def _load_dictionary():
    """load the English dictionary from words.txt if it exists.

    returns a set of lowercase words, or None if the file is absent.
    caches the result for the session.
    """
    global _english_words, _dictionary_available
    if _dictionary_available is not None:
        return _english_words

    if os.path.exists(settings.DICTIONARY_FILE):
        with open(settings.DICTIONARY_FILE, "r", encoding="utf-8") as f:
            _english_words = {line.strip().lower() for line in f if line.strip()}
        _dictionary_available = True
    else:
        _english_words = None
        _dictionary_available = False
    return _english_words


def _is_skippable(word):
    """return True if this word should not be spell-checked.

    skips: numbers, punctuation-only tokens, very short words (1 char).
    """
    if not word:
        return True
    if len(word) <= 1:
        return True
    if re.match(r'^[\d,._\-+*/=<>!@#$%^&()]+$', word):
        return True
    return False


def _is_known_word(word_lower, keyword_set, english_dict, user_words):
    """return True if the word is recognized (token, dictionary, or user-ignored)."""
    if word_lower in keyword_set:
        return True
    if word_lower in user_words:
        return True
    if english_dict is not None and word_lower in english_dict:
        return True
    return False


def _get_suggestions(word_lower, token_names):
    """find close matches for a misspelled word among token names/aliases."""
    return difflib.get_close_matches(word_lower, token_names, n=3, cutoff=0.7)


# sentinel: user chose "skip always" — caller should add to ignored words
_SKIP_ALWAYS = "__skip_always__"


def _remove_last_history_entry():
    """remove the last readline history entry.

    console.input() adds prompt answers (r, y, n, s) to readline history,
    polluting up-arrow recall. strip them immediately after each prompt.
    """
    length = readline.get_current_history_length()
    if length > 0:
        readline.remove_history_item(length - 1)


def _prompt_correction(word, suggestions, interactive):
    """ask the user which suggestion to accept.

    returns:
        (replacement_word, should_remember)
        replacement_word is None if user skips.
        replacement_word is _SKIP_ALWAYS if user chose skip always.
        should_remember is True if user chose to remember the correction.
    """
    if not interactive:
        return None, False

    if len(suggestions) == 1:
        console.print(
            f"[yellow]Unknown word:[/] [bold]{word}[/]  "
            f"[dim]Did you mean[/] [cyan]{suggestions[0]}[/][dim]?[/]"
        )
        console.print(
            r"  [green]\[y][/] correct  "
            r"  [green]\[r][/] correct & remember  "
            r"  [green]\[n][/] skip  "
            r"  [green]\[s][/] skip always"
        )
        answer = console.input("[yellow]> [/]").strip().lower()
        _remove_last_history_entry()
        if answer in ("r", "remember"):
            return suggestions[0], True
        if answer in ("y", "yes"):
            return suggestions[0], False
        if answer in ("s", "skip"):
            return _SKIP_ALWAYS, False
        return None, False

    # multiple suggestions
    console.print(
        f"[yellow]Unknown word:[/] [bold]{word}[/]  "
        f"[dim]Did you mean one of:[/]"
    )
    for i, s in enumerate(suggestions, 1):
        console.print(f"  [cyan]{i}[/]) {s}")
    console.print(
        r"  [green]\[1-{0}][/] correct  "
        r"[green]\[r1-r{0}][/] correct & remember  "
        r"  [green]\[n][/] skip  "
        r"  [green]\[s][/] skip always".format(len(suggestions))
    )
    answer = console.input("[yellow]> [/]").strip().lower()
    _remove_last_history_entry()
    # r1, r2, r3 — pick and remember
    if answer.startswith("r") and answer[1:].isdigit():
        idx = int(answer[1:]) - 1
        if 0 <= idx < len(suggestions):
            return suggestions[idx], True
    # 1, 2, 3 — pick without remembering
    if answer.isdigit():
        idx = int(answer) - 1
        if 0 <= idx < len(suggestions):
            return suggestions[idx], False
    if answer in ("s", "skip"):
        return _SKIP_ALWAYS, False
    return None, False


def spellcheck(sentence, interactive=True):
    """run spell correction on a sentence before the reduction loop.

    returns the (possibly corrected) sentence.
    only prompts in interactive mode (REPL). piped input is never corrected.
    """
    if not interactive:
        return sentence

    english_dict = _load_dictionary()
    user_words = load_user_words()
    corrections = load_corrections()
    keyword_map = get_all_keywords()
    keyword_set = {k.lower() for k in keyword_map}
    token_names = list(keyword_set)

    words = sentence.split()
    corrected = []
    changed = False

    for word in words:
        word_lower = word.lower()
        # strip trailing/leading punctuation for lookup (keep original for output)
        cleaned = word_lower.strip(".,;:!?\"'()[]{}") 

        # skip numbers, punctuation, single chars
        if _is_skippable(cleaned):
            corrected.append(word)
            continue

        # known word — no correction needed
        if _is_known_word(cleaned, keyword_set, english_dict, user_words):
            corrected.append(word)
            continue

        # auto-correct from remembered corrections
        if cleaned in corrections:
            corrected.append(corrections[cleaned])
            changed = True
            continue

        # in token-only mode (no dictionary), we can only flag words
        # that are close to a token — otherwise leave them alone
        suggestions = _get_suggestions(cleaned, token_names)
        if not suggestions:
            corrected.append(word)
            continue

        # prompt user
        replacement, should_remember = _prompt_correction(word, suggestions, interactive)
        if replacement is _SKIP_ALWAYS:
            add_word(cleaned)
            user_words.add(cleaned)
            corrected.append(word)
        elif replacement and should_remember:
            add_correction(cleaned, replacement)
            corrections[cleaned] = replacement
            corrected.append(replacement)
            changed = True
        elif replacement:
            corrected.append(replacement)
            changed = True
        else:
            corrected.append(word)

    result = " ".join(corrected)
    if changed:
        console.print(f"[dim]Corrected:[/] {result}")
    return result


def reset_cache():
    """reset the dictionary cache (for testing)."""
    global _english_words, _dictionary_available
    _english_words = None
    _dictionary_available = None
