"""
Token: clear
Aliases: cls, clrscr
Category: system
Priority: 1
Destructive: false

Clears the terminal screen.
"""

import os


def handle(sentence):
    """process one occurrence of 'clear' / 'cls' / 'clrscr' in the sentence.

    clears the terminal screen and returns any remaining text.

    examples:
        "clear"                -> "" (screen cleared)
        "cls"                  -> "" (screen cleared)
        "clrscr"              -> "" (screen cleared)
        "5 plus 3 clear"      -> "5 plus 3" (clear removed, screen cleared)
    """
    import re

    lower = sentence.lower()
    match = re.search(r'\b(clrscr|clear|cls)\b', lower)
    if not match:
        return sentence

    # clear the terminal
    os.system("clear" if os.name != "nt" else "cls")

    start, end = match.start(), match.end()
    before = sentence[:start].strip()
    after = sentence[end:].strip()

    parts = [p for p in (before, after) if p]
    return " ".join(parts)
