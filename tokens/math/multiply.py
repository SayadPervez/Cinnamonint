"""
Token: multiply
Aliases: multiplied
Category: math
Priority: 3
Destructive: false
"""

import re


def handle(sentence):
    """process one occurrence of 'multiply' or 'multiplied' in the sentence.

    examples:
        "multiply 5 by 3"          -> "15"
        "5 multiply 3"             -> "15"
        "5 multiplied by 3"        -> "15"
        "multiply 2, 3 and 4"      -> "24"
    """
    lower = sentence.lower()

    # match 'multiplied' first (longer), then 'multiply'
    match = re.search(r'\bmultiplied\b', lower)
    keyword = "multiplied"
    if not match:
        match = re.search(r'\bmultiply\b', lower)
        keyword = "multiply"
    if not match:
        return sentence

    start, end = match.start(), match.end()
    before = sentence[:start]
    after = sentence[end:]

    # remove optional "by" after the keyword
    after_stripped = re.sub(r'^\s+by\b', '', after)

    # extract numbers from left
    left_numbers = re.findall(r'[-+]?\d*\.?\d+', before)
    # extract first number from right
    right_match = re.match(r'\s*([-+]?\d*\.?\d+)(.*)', after_stripped)

    if left_numbers and right_match:
        left_val = float(left_numbers[-1])
        right_val = float(right_match.group(1))
        result = left_val * right_val
        remaining_before = _remove_last_number(before)
        remaining_after = right_match.group(2)
        result_str = _format_number(result)
        return f"{remaining_before}{result_str}{remaining_after}".strip()

    # "multiply X, Y, Z" form — multiply numbers up to the next token boundary
    if not left_numbers:
        from src.engine.tokenizer import find_token_boundary
        boundary = find_token_boundary(after_stripped, {"multiply", "multiplied"})
        work_area = after_stripped[:boundary]
        rest = after_stripped[boundary:]

        all_numbers = re.findall(r'[-+]?\d*\.?\d+', work_area)
        if all_numbers:
            product = 1.0
            for n in all_numbers:
                product *= float(n)
            result_str = _format_number(product)
            return f"{before.strip()} {result_str} {rest}".strip()

    return sentence


def _remove_last_number(s):
    return re.sub(r'\s*[-+]?\d*\.?\d+\s*$', ' ', s)


def _remove_leading_numbers(s):
    s = re.sub(r'^[\s,]*((?:[-+]?\d*\.?\d+[\s,]*(?:and\s*|by\s*)?)*[-+]?\d*\.?\d+)\s*', ' ', s)
    remaining = s.strip()
    if remaining and not re.match(r'^[-+]?\d*\.?\d+', remaining):
        return " " + remaining
    return ""


def _format_number(n):
    if n == int(n):
        return str(int(n))
    return str(n)
