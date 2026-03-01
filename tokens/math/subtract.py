"""
Token: subtract
Aliases: (none — 'minus' is a separate token)
Category: math
Priority: 2
Destructive: false
"""

import re


def handle(sentence):
    """process one occurrence of 'subtract' in the sentence.

    examples:
        "subtract 3 from 10"       -> "7"
        "10 subtract 3"            -> "7"
        "20 subtract 5 plus 3"     -> "15 plus 3"
    """
    lower = sentence.lower()
    match = re.search(r'\bsubtract\b', lower)
    if not match:
        return sentence

    start, end = match.start(), match.end()
    before = sentence[:start]
    after = sentence[end:]

    # check for "subtract X from Y" pattern
    from_match = re.match(r'\s*([-+]?\d*\.?\d+)\s+from\s+([-+]?\d*\.?\d+)(.*)', after)
    if from_match:
        subtrahend = float(from_match.group(1))
        minuend = float(from_match.group(2))
        result = minuend - subtrahend
        remaining = from_match.group(3)
        result_str = _format_number(result)
        return f"{before.strip()} {result_str}{remaining}".strip()

    # "X subtract Y" pattern
    left_numbers = re.findall(r'[-+]?\d*\.?\d+', before)
    right_match = re.match(r'\s*([-+]?\d*\.?\d+)(.*)', after)

    if left_numbers and right_match:
        left_val = float(left_numbers[-1])
        right_val = float(right_match.group(1))
        result = left_val - right_val
        remaining_before = _remove_last_number(before)
        remaining_after = right_match.group(2)
        result_str = _format_number(result)
        return f"{remaining_before}{result_str}{remaining_after}".strip()

    return sentence


def _remove_last_number(s):
    return re.sub(r'\s*[-+]?\d*\.?\d+\s*$', ' ', s)


def _format_number(n):
    if n == int(n):
        return str(int(n))
    return str(n)
