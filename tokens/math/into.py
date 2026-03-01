"""
Token: into
Category: math
Priority: 3
Destructive: false

'into' acts as multiplication: "5 into 6" -> "30"
"""

import re


def handle(sentence):
    """process one occurrence of 'into' in the sentence.

    examples:
        "5 into 6"             -> "30"
        "5 into 6 plus 2"     -> "30 plus 2"
    """
    lower = sentence.lower()
    match = re.search(r'\binto\b', lower)
    if not match:
        return sentence

    start, end = match.start(), match.end()
    before = sentence[:start]
    after = sentence[end:]

    left_numbers = re.findall(r'[-+]?\d*\.?\d+', before)
    right_match = re.match(r'\s*([-+]?\d*\.?\d+)(.*)', after)

    if left_numbers and right_match:
        left_val = float(left_numbers[-1])
        right_val = float(right_match.group(1))
        result = left_val * right_val
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
