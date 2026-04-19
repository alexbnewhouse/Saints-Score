"""Tests for saints_score.mentions.adjudicate — LLM response validation."""

from saints_score.mentions.adjudicate import _cache_key, _validate_llm_response


def test_validate_llm_response_good_input():
    raw = {
        "is_reference": True,
        "confidence": 0.85,
        "inferred_alias": "the saint",
        "is_oblique": False,
    }
    result = _validate_llm_response(raw)
    assert result["is_reference"] is True
    assert result["confidence"] == 0.85
    assert result["inferred_alias"] == "the saint"
    assert result["is_oblique"] is False


def test_validate_llm_response_coerces_types():
    """String confidence, missing fields, etc. should be coerced."""
    raw = {
        "is_reference": 1,  # truthy int
        "confidence": "0.5",  # string
        # inferred_alias missing
        # is_oblique missing
    }
    result = _validate_llm_response(raw)
    assert result["is_reference"] is True
    assert result["confidence"] == 0.5
    assert result["inferred_alias"] is None
    assert result["is_oblique"] is False


def test_validate_llm_response_empty():
    result = _validate_llm_response({})
    assert result["is_reference"] is False
    assert result["confidence"] == 0.0
    assert result["inferred_alias"] is None
    assert result["is_oblique"] is False


def test_cache_key_deterministic():
    k1 = _cache_key("hello world", "ATK-001", "gemma3:27b")
    k2 = _cache_key("hello world", "ATK-001", "gemma3:27b")
    assert k1 == k2


def test_cache_key_differs_on_model():
    k1 = _cache_key("hello", "ATK-001", "gemma3:27b")
    k2 = _cache_key("hello", "ATK-001", "llama3:8b")
    assert k1 != k2
