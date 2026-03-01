"""
Token: exit
Aliases: quit, q
Category: system
Priority: 0
Destructive: false

This token is handled directly by the REPL before reaching the engine.
If it somehow reaches the engine, it returns a signal string.
"""


def handle(sentence):
    """signal to exit. the REPL catches exit/quit before this is called."""
    return ""
