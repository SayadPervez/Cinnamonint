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

    from src.engine.tokenizer import find_token_boundary_reverse
    left_boundary = find_token_boundary_reverse(before, {"into"})
    left_region = before[left_boundary:]

    left_numbers = re.findall(r'[-+]?\d*\.?\d+', left_region)
    right_match = re.match(r'\s*([-+]?\d*\.?\d+)(.*)', after)

    if left_numbers and right_match:
        left_val = float(left_numbers[-1])
        right_val = float(right_match.group(1))
        result = left_val * right_val
        remaining_before = before[:left_boundary] + _remove_last_number(left_region)
        remaining_after = right_match.group(2)
        result_str = _format_number(result)
        return f"{remaining_before}{result_str}{remaining_after}".strip()

    return sentence


def _remove_last_number(s):
    """remove the last number and any trailing connectors from a string."""
    matches = list(re.finditer(r'[-+]?\d*\.?\d+', s))
    if not matches:
        return s
    return s[:matches[-1].start()]


def _format_number(n):
    if n == int(n):
        return str(int(n))
    return str(n)
