"""
Alias resolution and priority ordering — decide which token to process next.
"""


def resolve_next_token(found_tokens):
    """given a list of found tokens (from tokenizer), pick the one to process.

    rules:
        1. highest priority first
        2. among same priority, leftmost in sentence (lowest position)

    returns the chosen token dict or None if list is empty.
    """
    if not found_tokens:
        return None

    # sort by priority descending, then position ascending
    ordered = sorted(
        found_tokens,
        key=lambda t: (-t["token"]["priority"], t["position"]),
    )
    return ordered[0]


def resolve_keyword_to_token(keyword, keyword_map):
    """resolve a keyword (which may be an alias) to its canonical token dict.

    returns the token dict or None.
    """
    return keyword_map.get(keyword)
