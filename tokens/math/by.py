"""
Token: by
Category: math
Priority: 3
Destructive: false

'by' acts as division: "10 by 2" -> "5"
(only when used standalone, not as part of 'multiply by' or 'divide by')
"""

import re


def handle(sentence):
    """process one occurrence of standalone 'by' as division.

    examples:
        "10 by 2"              -> "5"
        "10 by 5 plus 3"      -> "2 plus 3"
    """
    lower = sentence.lower()

    # skip if 'by' is preceded by 'multiply'/'multiplied'/'divide'
    # those handlers consume their own 'by' (possibly with filler like "it"/"them")
    preceded = re.search(r'\b(?:multiply|multiplied|divide)\s+(?:(?:it|them)\s+)?by\b', lower)
    if preceded:
        # find a standalone 'by' that is NOT part of that pattern
        # search after the preceded match
        search_start = preceded.end()
        match = re.search(r'\bby\b', lower[search_start:])
        if match:
            match = re.search(r'\bby\b', lower[search_start:])
            if match:
                # adjust position
                actual_start = search_start + match.start()
                actual_end = search_start + match.end()
            else:
                return sentence
        else:
            return sentence
    else:
        match = re.search(r'\bby\b', lower)
        if not match:
            return sentence
        actual_start = match.start()
        actual_end = match.end()

    before = sentence[:actual_start]
    after = sentence[actual_end:]

    from src.engine.tokenizer import find_token_boundary_reverse
    left_boundary = find_token_boundary_reverse(before, {"by"})
    left_region = before[left_boundary:]

    left_numbers = re.findall(r'[-+]?\d*\.?\d+', left_region)
    right_match = re.match(r'\s*([-+]?\d*\.?\d+)(.*)', after)

    if left_numbers and right_match:
        left_val = float(left_numbers[-1])
        right_val = float(right_match.group(1))
        if right_val == 0:
            return sentence
        result = left_val / right_val
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
