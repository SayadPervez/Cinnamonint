"""
Token: wait
Aliases: pause
Category: utility
Priority: 1
Destructive: false

Pauses execution for a specified duration, printing a countdown,
then returns the remainder of the sentence for continued processing.
"""

import re
import sys
import time


# --- duration unit multipliers ---
_SECOND_WORDS = {"second", "seconds", "sec", "secs", "s"}
_MINUTE_WORDS = {"minute", "minutes", "min", "mins"}
_HOUR_WORDS = {"hour", "hours", "hr", "hrs"}
_UNIT_WORDS = _SECOND_WORDS | _MINUTE_WORDS | _HOUR_WORDS

# fractional modifiers — multiply the following value
_FRACTION_WORDS = {"half": 0.5, "quarter": 0.25, "quarters": 0.25}

# words that are part of the duration expression (not remainder)
_FILLER_WORDS = {"for", "a", "an", "of", "half", "quarter", "quarters"}
_DURATION_WORDS = _UNIT_WORDS | _FILLER_WORDS | _FRACTION_WORDS.keys()

_KEYWORDS = r'\b(?:wait|pause)\b'


def _split_duration_and_remainder(after):
    """split the text after 'wait' into a duration part and a remainder.

    boundary markers: 'and then', 'then'.
    'and' alone is tricky — it's a boundary only if the word after it
    is NOT a duration component (number, unit, filler).
    """
    words = after.split()
    i = 0
    while i < len(words):
        w = words[i].lower()

        # 'then' always marks the boundary
        if w == "then":
            remainder = " ".join(words[i + 1:]).strip()
            duration_part = " ".join(words[:i]).strip()
            return duration_part, remainder

        # 'and then' — two-word boundary
        if w == "and" and i + 1 < len(words) and words[i + 1].lower() == "then":
            remainder = " ".join(words[i + 2:]).strip()
            duration_part = " ".join(words[:i]).strip()
            return duration_part, remainder

        # 'and' alone — boundary only if next word isn't a duration component
        if w == "and" and i + 1 < len(words):
            next_w = words[i + 1].lower()
            is_duration = (
                next_w in _DURATION_WORDS
                or _is_number(next_w)
            )
            if not is_duration:
                remainder = " ".join(words[i + 1:]).strip()
                duration_part = " ".join(words[:i]).strip()
                return duration_part, remainder

        i += 1

    return after.strip(), ""


def _is_number(s):
    """check if a string is a numeric value."""
    try:
        float(s)
        return True
    except ValueError:
        return False


def _parse_duration(text):
    """parse a natural-language duration string into total seconds.

    tokenises left-to-right, assembling (number × fraction × unit) groups.

    supported patterns:
        5                           -> 5s
        10 seconds                  -> 10s
        2 minutes                   -> 120s
        a minute                    -> 60s
        half a minute               -> 30s
        quarter of a minute         -> 15s
        2 quarters of a min         -> 30s
        a quarter of an hour        -> 900s
        1 minute and 30 seconds     -> 90s
        2 and a half minutes        -> 150s
        half                        -> 0.5s
        for 5 secs                  -> 5s
    """
    if not text.strip():
        return 0.0

    words = text.lower().split()
    # remove filler words that carry no numeric meaning
    words = [w for w in words if w not in ("for", "of")]
    if not words:
        return 0.0

    total = 0.0
    i = 0

    while i < len(words):
        w = words[i]

        # skip 'and' connectors between compound groups
        if w == "and":
            i += 1
            continue

        # --- build one duration group: number * fraction * unit ---
        number = None
        fraction = 1.0

        # step 1: try to read a leading number
        if _is_number(w):
            number = float(w)
            i += 1
            if i >= len(words):
                # bare trailing number — seconds
                total += number
                break
            w = words[i]

            # peek ahead for "and a half/quarter <unit>" pattern
            # e.g. "2 and a half minutes" = (2 + 0.5) * 60
            if w == "and" and i + 1 < len(words):
                rest = words[i + 1:]
                frac_offset = _peek_and_fraction(rest)
                if frac_offset is not None:
                    frac_val, unit_mult, consumed = frac_offset
                    total += (number + frac_val) * unit_mult
                    i += 1 + consumed  # skip 'and' + consumed words
                    continue

        elif w in ("a", "an"):
            number = 1.0
            i += 1
            if i >= len(words):
                total += 1.0
                break
            w = words[i]

        # step 2: try to read a fraction modifier (half, quarter, quarters)
        if w in _FRACTION_WORDS:
            fraction = _FRACTION_WORDS[w]
            # if we had a number, it multiplies the fraction (2 quarters = 0.5)
            if number is not None:
                fraction = number * _FRACTION_WORDS[w]
                number = None  # consumed into fraction
            i += 1
            # skip optional 'a' / 'an' after fraction
            if i < len(words) and words[i] in ("a", "an"):
                i += 1
            if i >= len(words):
                # bare fraction — default to seconds
                total += fraction
                break
            w = words[i]

        # step 3: try to read a unit
        if w in _UNIT_WORDS:
            multiplier = _unit_to_seconds(w)
            if number is not None and fraction != 1.0:
                total += number * fraction * multiplier
            elif number is not None:
                total += number * multiplier
            elif fraction != 1.0:
                total += fraction * multiplier
            else:
                total += multiplier
            i += 1
        else:
            # no unit — value defaults to seconds
            if number is not None and fraction != 1.0:
                total += number * fraction
            elif number is not None:
                total += number
            elif fraction != 1.0:
                total += fraction
            else:
                # unrecognized word — skip
                i += 1

    return total


def _peek_and_fraction(rest):
    """check if words after 'and' form a 'a half/quarter <unit>' pattern.

    rest: list of words after 'and' (already lowercase).
    returns (fraction_value, unit_multiplier, words_consumed) or None.
    """
    idx = 0

    # optional 'a' / 'an'
    if idx < len(rest) and rest[idx] in ("a", "an"):
        idx += 1

    # must have a fraction word
    if idx >= len(rest) or rest[idx] not in _FRACTION_WORDS:
        return None

    frac_val = _FRACTION_WORDS[rest[idx]]
    idx += 1

    # skip optional 'a' / 'an' after fraction (e.g. "half a minute")
    if idx < len(rest) and rest[idx] in ("a", "an"):
        idx += 1

    # must have a unit
    if idx >= len(rest) or rest[idx] not in _UNIT_WORDS:
        return None

    unit_mult = _unit_to_seconds(rest[idx])
    idx += 1

    return frac_val, unit_mult, idx


def _unit_to_seconds(unit):
    """convert a unit word to its multiplier in seconds."""
    if unit in _SECOND_WORDS:
        return 1.0
    if unit in _MINUTE_WORDS:
        return 60.0
    if unit in _HOUR_WORDS:
        return 3600.0
    return 1.0


def _countdown(total_seconds):
    """print a countdown and sleep for the given duration."""
    remaining = int(total_seconds)
    if remaining <= 0:
        return

    # for fractional seconds less than 1, just sleep
    if total_seconds < 1:
        print(f"\u23f3 {total_seconds:.1f}s...")
        time.sleep(total_seconds)
        return

    for s in range(remaining, 0, -1):
        print(f"\u23f3 {s}s remaining...")
        time.sleep(1)

    # handle any fractional remainder
    frac = total_seconds - remaining
    if frac > 0:
        time.sleep(frac)

    print("\u23f3 done!")


def handle(sentence):
    """process one occurrence of 'wait'/'pause' in the sentence.

    examples:
        "wait 5"                           -> "" (sleeps 5s)
        "wait for 5 seconds and then say done" -> "say done" (sleeps 5s)
        "wait a minute and say hello"      -> "say hello" (sleeps 60s)
    """
    lower = sentence.lower()
    match = re.search(_KEYWORDS, lower)
    if not match:
        return sentence

    start, end = match.start(), match.end()
    before = sentence[:start].strip()
    # consume trailing punctuation after keyword
    while end < len(sentence) and sentence[end] in ".,;:!?":
        end += 1
    after = sentence[end:].strip()

    duration_text, remainder = _split_duration_and_remainder(after)
    total_seconds = _parse_duration(duration_text)

    _countdown(total_seconds)

    if before and remainder:
        return f"{before} {remainder}"
    if before:
        return before
    return remainder
