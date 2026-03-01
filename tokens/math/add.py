"""
Token: add
Aliases: (none — 'plus' is a separate token)
Category: math
Priority: 2
Destructive: false

'add' works like 'plus'. "add 5, 6, and 7" -> sums all numbers.
"5 add 3" -> "8"
"""

import re


def handle(sentence):
    """process one occurrence of 'add' in the sentence.

    examples:
        "add 5 6 7"            -> "18"
        "add 5, 6 and 7"      -> "18"
        "3 add 5"              -> "8"
        "add 5 6 and subtract 3" -> "11 and subtract 3"
    """
    lower = sentence.lower()
    match = re.search(r'\badd\b', lower)
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
        left_val = sum(float(n) for n in left_numbers)
        right_val = float(right_match.group(1))
        result = left_val + right_val
        remaining_before = _remove_numbers_from_end(before)
        remaining_after = right_match.group(2)
        result_str = _format_number(result)
        return f"{remaining_before}{result_str}{remaining_after}".strip()

    # "add X, Y, Z" form — sum numbers up to the next token boundary
    from src.engine.tokenizer import find_token_boundary
    boundary = find_token_boundary(after, "add")
    work_area = after[:boundary]
    rest = after[boundary:]

    all_numbers = re.findall(r'[-+]?\d*\.?\d+', work_area)
    if all_numbers:
        total = sum(float(n) for n in left_numbers) + sum(float(n) for n in all_numbers)
        result_str = _format_number(total)
        return f"{before.strip()} {result_str} {rest}".strip()

    return sentence


def _remove_numbers_from_end(s):
    """remove trailing number expressions from a string."""
    s = re.sub(r'[\s,]*([-+]?\d*\.?\d+[\s,]*(?:and\s*)?)+\s*$', ' ', s)
    return s


def _remove_leading_numbers(s):
    """remove leading numbers, commas, 'and' from a string."""
    s = re.sub(r'^[\s,]*((?:[-+]?\d*\.?\d+[\s,]*(?:and\s*)?)*[-+]?\d*\.?\d+)\s*', ' ', s)
    # check if there's remaining non-number text
    remaining = s.strip()
    if remaining and not re.match(r'^[-+]?\d*\.?\d+', remaining):
        return " " + remaining
    return ""


def _format_number(n):
    if n == int(n):
        return str(int(n))
    return str(n)
