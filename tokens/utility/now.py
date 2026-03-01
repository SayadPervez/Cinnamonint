"""
Token: now
Category: utility
Priority: 1
Destructive: false

Reports both date and time.
"""

import re
from datetime import datetime


def handle(sentence):
    """replace 'now' with the current date and time.

    examples:
        "now"                 -> "02 March 2026 14:30:45"
        "what is now"         -> "what is 02 March 2026 14:30:45"
    """
    lower = sentence.lower()
    match = re.search(r'\bnow\b', lower)
    if not match:
        return sentence

    dt = datetime.now()
    dt_str = dt.strftime("%d %B %Y %H:%M:%S")

    result = sentence[:match.start()] + dt_str + sentence[match.end():]
    return result
