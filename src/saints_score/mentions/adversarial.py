"""Adversarial language normalisation for 4chan /pol/ text.

Handles the many ways /pol/ users obfuscate attacker references:
- Leetspeak substitutions (e.g., "t4rr4nt", "br31v1k")
- Unicode homoglyphs (Cyrillic а for Latin a, etc.)
- Vowel dropping / consonant-only spelling ("Trrnt", "Brvsn")
- Deliberate misspelllings and phonetic spelling ("crewseus", "tarant")
- Zalgo text / combining diacriticals
- Nickname evolution (tracking how oblique references emerge and shift)

Based on:
- Ali, Blackburn & Stringhini (2025). "Evolving hate speech online."
- Bermudez-Villalva & Mehrnezhad (2025). "Measuring Online Hate on 4chan."
"""

from __future__ import annotations

import re
import unicodedata
from typing import TYPE_CHECKING

from saints_score.logging import logger

if TYPE_CHECKING:
    pass

# ── Leetspeak mappings ────────────────────────────────────────────────────

# Common leet substitutions seen on /pol/
_LEET_MAP: dict[str, str] = {
    "0": "o",
    "1": "i",
    "3": "e",
    "4": "a",
    "5": "s",
    "7": "t",
    "8": "b",
    "9": "g",
    "@": "a",
    "$": "s",
    "!": "i",
    "|": "l",
    "+": "t",
    "}{": "h",
}

# ── Unicode homoglyph mappings ────────────────────────────────────────────

# Cyrillic → Latin for the most common confusables
_HOMOGLYPH_MAP: dict[str, str] = {
    "\u0410": "A",  # А → A
    "\u0412": "B",  # В → B
    "\u0421": "C",  # С → C
    "\u0415": "E",  # Е → E
    "\u041d": "H",  # Н → H
    "\u041a": "K",  # К → K
    "\u041c": "M",  # М → M
    "\u041e": "O",  # О → O
    "\u0420": "P",  # Р → P
    "\u0422": "T",  # Т → T
    "\u0425": "X",  # Х → X
    "\u0430": "a",  # а → a
    "\u0435": "e",  # е → e
    "\u043e": "o",  # о → o
    "\u0440": "p",  # р → p
    "\u0441": "c",  # с → c
    "\u0443": "y",  # у → y
    "\u0445": "x",  # х → x
    # Greek
    "\u0391": "A",  # Α → A
    "\u0392": "B",  # Β → B
    "\u0395": "E",  # Ε → E
    "\u0397": "H",  # Η → H
    "\u0399": "I",  # Ι → I
    "\u039a": "K",  # Κ → K
    "\u039c": "M",  # Μ → M
    "\u039d": "N",  # Ν → N
    "\u039f": "O",  # Ο → O
    "\u03a1": "P",  # Ρ → P
    "\u03a4": "T",  # Τ → T
    "\u03a7": "X",  # Χ → X
    "\u03b1": "a",  # α → a (when used as homoglyph)
    "\u03bf": "o",  # ο → o
}

# Regex for Zalgo text / combining marks (keep basic accents)
_ZALGO_RE = re.compile(
    r"[\u0300-\u036f\u0489\u1dc0-\u1dff\u20d0-\u20ff\ufe20-\ufe2f]{2,}"
)

# Regex for repeated chars (3+ of the same)
_REPEATED_CHAR_RE = re.compile(r"(.)\1{2,}")


def deleet(text: str) -> str:
    """Reverse common leetspeak substitutions.

    >>> deleet("t4rr4nt")
    'tarrant'
    >>> deleet("br31v1k")
    'breivik'
    """
    result = []
    i = 0
    while i < len(text):
        # Check two-char sequences first
        if i + 1 < len(text):
            pair = text[i : i + 2]
            if pair in _LEET_MAP:
                result.append(_LEET_MAP[pair])
                i += 2
                continue
        ch = text[i]
        if ch in _LEET_MAP:
            result.append(_LEET_MAP[ch])
        else:
            result.append(ch)
        i += 1
    return "".join(result)


def dehomoglyph(text: str) -> str:
    """Replace Cyrillic/Greek homoglyphs with Latin equivalents.

    >>> dehomoglyph("Таrrаnt")  # Cyrillic T and а
    'Tarrant'
    """
    return "".join(_HOMOGLYPH_MAP.get(ch, ch) for ch in text)


def strip_zalgo(text: str) -> str:
    """Remove excessive combining diacriticals (Zalgo text).

    Keeps single combining marks (for legitimate accented characters)
    but strips runs of 2+ combining characters.
    """
    return _ZALGO_RE.sub("", text)


def collapse_repeats(text: str, max_repeat: int = 2) -> str:
    """Collapse runs of 3+ repeated characters to at most ``max_repeat``.

    >>> collapse_repeats("taaaaarrant")
    'taarrant'
    """
    def _sub(m: re.Match) -> str:
        return m.group(1) * max_repeat

    return _REPEATED_CHAR_RE.sub(_sub, text)


def normalize_adversarial(text: str) -> str:
    """Full adversarial normalisation pipeline.

    Applies: NFKC → homoglyph → Zalgo strip → leetspeak → repeat collapse
    → lowercase → whitespace normalisation.

    This is designed as a *candidate-generation* step, not a final classifier.
    The normalised text feeds into fuzzy/exact matching to expand recall;
    downstream transformer-based classifiers handle precision.
    """
    # NFKC first (compatibility decomposition)
    text = unicodedata.normalize("NFKC", text)
    # Homoglyphs
    text = dehomoglyph(text)
    # Zalgo
    text = strip_zalgo(text)
    # Leetspeak
    text = deleet(text)
    # Collapse repeated chars
    text = collapse_repeats(text)
    # Lowercase and normalise whitespace
    text = text.lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ── Phonetic normalisation ────────────────────────────────────────────────

# Simplified Soundex-like reduction: strip vowels + deduplicate consonants
_VOWELS = frozenset("aeiou")


def consonant_skeleton(word: str) -> str:
    """Reduce a word to its consonant skeleton for phonetic-ish matching.

    Keeps first letter, strips vowels, deduplicates consecutive consonants.

    >>> consonant_skeleton("tarrant")
    'trnt'
    >>> consonant_skeleton("tarant")
    'trnt'
    """
    word = word.lower()
    if not word:
        return ""

    result = [word[0]] if word[0] not in _VOWELS else []
    prev = word[0]
    for ch in word[1:]:
        if ch in _VOWELS:
            continue
        if ch == prev:
            continue
        result.append(ch)
        prev = ch
    return "".join(result)


def generate_adversarial_variants(alias: str) -> list[str]:
    """Generate common adversarial variants of an alias for expanded matching.

    Produces: original, leet variants, vowel-dropped, consonant skeleton.
    """
    alias_lower = alias.lower()
    variants = {alias_lower}

    # Consonant skeleton
    skel = consonant_skeleton(alias_lower)
    if len(skel) >= 3:
        variants.add(skel)

    # Vowel-dropped
    no_vowels = "".join(c for c in alias_lower if c not in _VOWELS)
    if len(no_vowels) >= 3:
        variants.add(no_vowels)

    # Common leet substitutions (forward: a→4, e→3, etc.)
    leet_forward = alias_lower
    for latin, leet in [("a", "4"), ("e", "3"), ("i", "1"), ("o", "0"), ("s", "5"), ("t", "7")]:
        leet_forward = leet_forward.replace(latin, leet)
    variants.add(leet_forward)

    return sorted(variants)
