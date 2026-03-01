"""
Token: say
Aliases: speak, tell
Category: system
Priority: 1
Destructive: false

Outputs everything after 'say' as text.
"""

import re


def handle(sentence):
    """process one occurrence of 'say' in the sentence.

    examples:
        "say hello world"     -> "hello world"
        "say 5 plus 3"        -> "5 plus 3"  (other tokens process first due to priority)
    """
    lower = sentence.lower()
    match = re.search(r'\bsay\b', lower)
    if not match:
        return sentence

    start, end = match.start(), match.end()
    before = sentence[:start].strip()
    after = sentence[end:].strip()

    # 'say' outputs what follows it
    if before:
        return f"{before} {after}".strip()
    return after
