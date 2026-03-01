"""
Token: minus
Aliases: (none — 'subtract' is a separate token)
Category: math
Priority: 2
Destructive: false
"""

import re


def handle(sentence):
    """process one occurrence of 'minus' in the sentence.

    examples:
        "10 minus 3"            -> "7"
        "10 minus 3 plus 2"    -> "7 plus 2"
    """
    lower = sentence.lower()
    match = re.search(r'\bminus\b', lower)
    if not match:
        return sentence

    start, end = match.start(), match.end()
    before = sentence[:start]
    after = sentence[end:]

    # get the last number before 'minus'
    left_numbers = re.findall(r'[-+]?\d*\.?\d+', before)
    # get the first number after 'minus'
    right_match = re.match(r'\s*([-+]?\d*\.?\d+)(.*)', after)

    if left_numbers and right_match:
        left_val = float(left_numbers[-1])
        right_val = float(right_match.group(1))
        result = left_val - right_val

        # remove the consumed left number
        remaining_before = _remove_last_number(before)
        remaining_after = right_match.group(2)
        result_str = _format_number(result)
        return f"{remaining_before}{result_str}{remaining_after}".strip()

    return sentence


def _remove_last_number(s):
    """remove the last number from a string."""
    return re.sub(r'\s*[-+]?\d*\.?\d+\s*$', ' ', s)


def _format_number(n):
    if n == int(n):
        return str(int(n))
    return str(n)
