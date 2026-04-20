"""Tests for saints_score.mentions.adversarial — adversarial text normalisation."""

from saints_score.mentions.adversarial import (
    collapse_repeats,
    consonant_skeleton,
    dehomoglyph,
    deleet,
    generate_adversarial_variants,
    normalize_adversarial,
    strip_zalgo,
)


# ── deleet ──────────────────────────────────────────────────────────

def test_deleet_simple():
    assert deleet("t4rr4nt") == "tarrant"


def test_deleet_mixed():
    assert deleet("cr00si0us") == "croosious"


def test_deleet_no_leet():
    assert deleet("normal text") == "normal text"


def test_deleet_all_digits():
    assert deleet("1337") == "ieet"


# ── dehomoglyph ────────────────────────────────────────────────────

def test_dehomoglyph_cyrillic():
    # Cyrillic а → a, е → e, о → o
    result = dehomoglyph("tаrrаnt")  # 'а' is Cyrillic
    assert result == "tarrant"


def test_dehomoglyph_no_change():
    assert dehomoglyph("tarrant") == "tarrant"


# ── strip_zalgo ────────────────────────────────────────────────────

def test_strip_zalgo():
    # Zalgo text with runs of combining chars (2+ in sequence)
    zalgo = "t\u0300\u0301\u0302a\u0303\u0304\u0305r\u0306\u0307r\u0308\u0309a\u030a\u030bn\u030c\u030dt"
    result = strip_zalgo(zalgo)
    assert result == "tarrant"


def test_strip_zalgo_normal():
    assert strip_zalgo("hello world") == "hello world"


# ── collapse_repeats ───────────────────────────────────────────────

def test_collapse_repeats():
    assert collapse_repeats("taaaarrant") == "taarrant"


def test_collapse_repeats_normal():
    assert collapse_repeats("tarrant") == "tarrant"


# ── normalize_adversarial ──────────────────────────────────────────

def test_normalize_adversarial_chain():
    """All normalisations should be applied in sequence."""
    # Leet + repeated chars
    result = normalize_adversarial("t4rr4444nt")
    assert "tarr" in result
    assert "nt" in result


def test_normalize_adversarial_passthrough():
    assert normalize_adversarial("tarrant") == "tarrant"


# ── consonant_skeleton ─────────────────────────────────────────────

def test_consonant_skeleton():
    assert consonant_skeleton("tarrant") == "trnt"


def test_consonant_skeleton_vowel_only():
    assert consonant_skeleton("oui") == ""


def test_consonant_skeleton_empty():
    assert consonant_skeleton("") == ""


# ── generate_adversarial_variants ──────────────────────────────────

def test_generate_variants_contains_original():
    variants = generate_adversarial_variants("tarrant")
    assert "tarrant" in variants


def test_generate_variants_leet():
    variants = generate_adversarial_variants("tarrant")
    # Should include at least some leet variants
    assert any(c.isdigit() for v in variants for c in v)


def test_generate_variants_vowel_dropped():
    variants = generate_adversarial_variants("tarrant")
    assert "trnt" in variants


def test_generate_variants_short_alias():
    """Short aliases should still produce some variants."""
    variants = generate_adversarial_variants("bt")
    assert "bt" in variants
    # Should have at least the original
    assert len(variants) >= 1
