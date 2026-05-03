"""
User dictionary — persistent ignore list and remembered corrections
for spellcheck.

- Ignored words: data/user_dictionary.json (JSON array of words)
- Remembered corrections: data/corrections.json (JSON dict of typo → correction)
"""

import json
import os

from src.config import settings


def _ensure_data_dir():
    """create data/ directory if it doesn't exist."""
    os.makedirs(settings.DATA_DIR, exist_ok=True)


# --- ignored words ---

def _save_user_words(words):
    """write the full word set to disk as a sorted JSON array."""
    with open(settings.USER_DICTIONARY_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(words), f, indent=2)


def load_user_words():
    """load user-ignored words from disk. returns a set of lowercase words."""
    if not os.path.exists(settings.USER_DICTIONARY_FILE):
        return set()
    with open(settings.USER_DICTIONARY_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except (json.JSONDecodeError, ValueError):
            return set()
    if not isinstance(data, list):
        return set()
    return {w.strip().lower() for w in data if isinstance(w, str) and w.strip()}


def add_word(word):
    """add a word to the user dictionary (persisted immediately).

    also removes the word from corrections if present (mutual exclusivity).
    """
    word = word.strip().lower()
    if not word:
        return
    existing = load_user_words()
    if word in existing:
        return
    # mutual exclusivity: remove from corrections if present
    remove_correction(word)
    _ensure_data_dir()
    existing.add(word)
    _save_user_words(existing)


def remove_word(word):
    """remove a word from the user dictionary. returns True if found, False if not."""
    word = word.strip().lower()
    existing = load_user_words()
    if word not in existing:
        return False
    existing.discard(word)
    _ensure_data_dir()
    _save_user_words(existing)
    return True


def list_words():
    """return a sorted list of all user-ignored words."""
    return sorted(load_user_words())


# --- remembered corrections ---

def load_corrections():
    """load remembered corrections from disk.

    returns a dict mapping typo → correction (both lowercase).
    stored as a JSON object.
    """
    if not os.path.exists(settings.CORRECTIONS_FILE):
        return {}
    with open(settings.CORRECTIONS_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except (json.JSONDecodeError, ValueError):
            return {}
    return {k.lower(): v.lower() for k, v in data.items()}


def add_correction(typo, correction):
    """remember a correction (persisted immediately).

    also removes the typo from ignored words if present (mutual exclusivity).
    """
    typo = typo.strip().lower()
    correction = correction.strip().lower()
    if not typo or not correction:
        return
    # mutual exclusivity: remove from ignored words if present
    remove_word(typo)
    existing = load_corrections()
    existing[typo] = correction
    _save_corrections(existing)


def remove_correction(typo):
    """remove a remembered correction. returns True if found."""
    typo = typo.strip().lower()
    existing = load_corrections()
    if typo not in existing:
        return False
    del existing[typo]
    _save_corrections(existing)
    return True


def list_corrections():
    """return a sorted list of (typo, correction) tuples."""
    return sorted(load_corrections().items())


def _save_corrections(corrections):
    """write the full corrections dict to disk as JSON."""
    _ensure_data_dir()
    with open(settings.CORRECTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(corrections.items())), f, indent=2, ensure_ascii=False)
