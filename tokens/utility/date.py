"""
Token: date
Aliases: today
Category: utility
Priority: 1
Destructive: false
"""

import re
from datetime import datetime


def handle(sentence):
    """replace 'date' with the current date.

    examples:
        "date"                -> "02 March 2026"
        "what is the date"    -> "what is the 02 March 2026"
    """
    lower = sentence.lower()
    match = re.search(r'\bdate\b', lower)
    if not match:
        return sentence

    now = datetime.now()
    date_str = now.strftime("%d %B %Y")

    result = sentence[:match.start()] + date_str + sentence[match.end():]
    return result
