"""
Token: hi
Aliases: hey, hello, greetings, howdy, sup
Category: system
Priority: 1
Destructive: false

Prints a random greeting from a preset list, then returns
the remainder of the sentence for continued processing.
"""

import random
import re


GREETINGS = [
    "Hey there! I'm Cinnamonint — your command-line sentence engine.",
    "Hello! Cinnamonint at your service.",
    "Greetings! Ready to crunch some sentences.",
    "Hi! Type a sentence and watch it reduce.",
    "Howdy! Let's get to work.",
]

_KEYWORDS = r'\b(?:hey there|hi|hey|hello|greetings|howdy|sup)\b'


def handle(sentence):
    """process one occurrence of a greeting keyword in the sentence.

    examples:
        "hi"                    -> "" (prints greeting)
        "hey multiply 5 and 6"  -> "multiply 5 and 6" (prints greeting)
        "say hi to everyone"    -> "say to everyone" (prints greeting)
    """
    lower = sentence.lower()
    match = re.search(_KEYWORDS, lower)
    if not match:
        return sentence

    greeting = random.choice(GREETINGS)
    print(greeting)

    start, end = match.start(), match.end()
    # consume any trailing punctuation glued to the keyword (e.g. "hi," "hey!")
    while end < len(sentence) and sentence[end] in ".,;:!?":
        end += 1
    before = sentence[:start].strip()
    after = sentence[end:].strip()

    if before:
        return f"{before} {after}".strip()
    return after
