"""
Token: divide
Aliases: (none — 'by' is a separate token)
Category: math
Priority: 3
Destructive: false
"""

import re


def handle(sentence):
    """process one occurrence of 'divide' in the sentence.

    examples:
        "divide 10 by 2"       -> "5"
        "10 divide 2"          -> "5"
        "10 divide by 2"       -> "5"
        "20 divide 4 plus 3"   -> "5 plus 3"
    """
    lower = sentence.lower()
    match = re.search(r'\bdivide\b', lower)
    if not match:
        return sentence

    start, end = match.start(), match.end()
    before = sentence[:start]
    after = sentence[end:]

    # remove optional "by" after divide
    after_stripped = re.sub(r'^\s+by\b', '', after)

    # extract numbers
    left_numbers = re.findall(r'[-+]?\d*\.?\d+', before)
    right_match = re.match(r'\s*([-+]?\d*\.?\d+)(.*)', after_stripped)

    if left_numbers and right_match:
        left_val = float(left_numbers[-1])
        right_val = float(right_match.group(1))
        if right_val == 0:
            return sentence  # division by zero — leave unchanged
        result = left_val / right_val
        remaining_before = _remove_last_number(before)
        remaining_after = right_match.group(2)
        result_str = _format_number(result)
        return f"{remaining_before}{result_str}{remaining_after}".strip()

    # "divide X by Y" with no left number — respect token boundaries
    if not left_numbers:
        from src.engine.tokenizer import find_token_boundary
        boundary = find_token_boundary(after_stripped, {"divide", "by"})
        work_area = after_stripped[:boundary]
        rest = after_stripped[boundary:]

        parts = re.findall(r'[-+]?\d*\.?\d+', work_area)
        if len(parts) >= 2:
            dividend = float(parts[0])
            divisor = float(parts[1])
            if divisor == 0:
                return sentence
            result = dividend / divisor
            remaining = _remove_leading_n_numbers(work_area, 2).strip()
            result_str = _format_number(result)
            parts_out = [before.strip(), result_str]
            if remaining:
                parts_out.append(remaining)
            if rest.strip():
                parts_out.append(rest.strip())
            return " ".join(p for p in parts_out if p)

    return sentence


def _remove_last_number(s):
    return re.sub(r'\s*[-+]?\d*\.?\d+\s*$', ' ', s)


def _remove_leading_n_numbers(s, n):
    """remove the first n numbers from a string."""
    for _ in range(n):
        s = re.sub(r'^[\s,]*(?:by\s+)?[-+]?\d*\.?\d+', '', s, count=1)
    return s


def _format_number(n):
    if n == int(n):
        return str(int(n))
    return str(n)
