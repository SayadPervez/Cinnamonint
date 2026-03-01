"""
Token: plus
Aliases: +
Category: math
Priority: 2
Destructive: false
"""

import re


def handle(sentence):
    """process one occurrence of 'plus' in the sentence.

    examples:
        "5 plus 3"          -> "8"
        "5 plus 3 minus 1"  -> "8 minus 1"
        "10 plus 20 plus 5" -> "30 plus 5"  (one occurrence per call)
    """
    lower = sentence.lower()
    match = re.search(r'\bplus\b', lower)
    if not match:
        return sentence

    start, end = match.start(), match.end()
    before = sentence[:start]
    after = sentence[end:]

    # extract numbers from left side
    left_numbers = re.findall(r'[-+]?\d*\.?\d+', before)
    # extract the first number from right side
    right_match = re.match(r'\s*([-+]?\d*\.?\d+)(.*)', after)

    if left_numbers and right_match:
        left_val = float(left_numbers[-1])
        right_val = float(right_match.group(1))
        result = left_val + right_val
        # clean up: remove the consumed left number from before
        remaining_before = _remove_last_number(before)
        remaining_after = right_match.group(2)
        result_str = _format_number(result)
        return f"{remaining_before}{result_str}{remaining_after}".strip()

    return sentence


def _remove_last_number(s):
    """remove the last number from a string."""
    return re.sub(r'\s*[-+]?\d*\.?\d+\s*$', ' ', s)


def _format_number(n):
    """format a number — integer if whole, float otherwise."""
    if n == int(n):
        return str(int(n))
    return str(n)
