"""
Token: time
Aliases: (none)
Category: utility
Priority: 1
Destructive: false
"""

import re
from datetime import datetime


def handle(sentence):
    """replace 'time' with the current time.

    examples:
        "time"                -> "14:30:45"
        "say the time"        -> "say the 14:30:45"
        "what is the time"    -> "what is the 14:30:45"
    """
    lower = sentence.lower()
    match = re.search(r'\btime\b', lower)
    if not match:
        return sentence

    now = datetime.now()
    time_str = now.strftime("%H:%M:%S")

    # replace the keyword with the time string
    result = sentence[:match.start()] + time_str + sentence[match.end():]
    return result
