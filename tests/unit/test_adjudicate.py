"""Tests for saints_score.mentions.adjudicate — cross-encoder adjudication."""

from unittest.mock import MagicMock, patch

import numpy as np
import polars as pl
import pytest

from saints_score.mentions.adjudicate import (
    _OBLIQUE_MATCH_TYPES,
    _sigmoid,
    adjudicate_candidates,
    filter_mentions,
)


# ── _sigmoid ─────────────────────────────────────────────────────────────


def test_sigmoid_zero():
    assert _sigmoid(np.array([0.0]))[0] == pytest.approx(0.5)


def test_sigmoid_large_positive():
    assert _sigmoid(np.array([100.0]))[0] == pytest.approx(1.0, abs=1e-6)


def test_sigmoid_large_negative():
    assert _sigmoid(np.array([-100.0]))[0] == pytest.approx(0.0, abs=1e-6)


def test_sigmoid_numerically_stable():
    """No overflow/nan for extreme values."""
    vals = np.array([-1000.0, -500.0, 0.0, 500.0, 1000.0])
    out = _sigmoid(vals)
    assert not np.any(np.isnan(out))
    assert not np.any(np.isinf(out))


# ── _OBLIQUE_MATCH_TYPES constant ─────────────────────────────────────────


def test_oblique_types_includes_semantic_and_phonetic():
    assert "semantic" in _OBLIQUE_MATCH_TYPES
    assert "phonetic_skeleton" in _OBLIQUE_MATCH_TYPES


def test_oblique_types_excludes_exact():
    assert "exact_substring" not in _OBLIQUE_MATCH_TYPES
    assert "fuzzy" not in _OBLIQUE_MATCH_TYPES


# ── adjudicate_candidates — tiering logic ─────────────────────────────────


def _make_cfg(tmp_path):
    from saints_score.config import Settings
    return Settings(
        project_root=tmp_path,
        cross_encoder_model="cross-encoder/ms-marco-MiniLM-L-6-v2",
        cross_encoder_batch_size=32,
        mention_confidence_threshold=0.5,
    )


def _make_cases():
    return pl.DataFrame({
        "case_id": ["ATK-001", "ATK-002"],
        "perpetrator_name": ["Alice Attacker", "Bob Bomber"],
        "event_year": [2020, 2021],
        "country": ["US", "UK"],
        "method_primary": ["firearm", "vehicle"],
        "venue_type": ["school", "market"],
        "fatalities_excl_perp": [5, 3],
    })


def _make_posts():
    return pl.DataFrame({
        "post_id": [1, 2, 3, 4],
        "body_clean": [
            "Alice Attacker did nothing wrong",
            "Some unrelated post",
            "Bob Bomber was based",
            "alc4 att4ck3r lol",
        ],
    })


def test_exact_substring_auto_accepted(tmp_path):
    """exact_substring candidates are accepted unconditionally without model."""
    cfg = _make_cfg(tmp_path)
    candidates = pl.DataFrame({
        "post_id": [1, 2],
        "attacker_id": ["ATK-001", "ATK-002"],
        "match_type": ["exact_substring", "exact_substring"],
        "alias_matched": ["alice attacker", "bob bomber"],
    })
    posts = _make_posts()
    cases = _make_cases()

    # No cross-encoder should be loaded for exact-only candidates
    with patch("saints_score.mentions.adjudicate._get_cross_encoder") as mock_ce:
        result = adjudicate_candidates(candidates, posts, cases, cfg)
        mock_ce.assert_not_called()

    assert result.height == 2
    assert result["is_reference"].to_list() == [True, True]
    assert result["confidence"].to_list() == [1.0, 1.0]
    assert result["is_oblique"].to_list() == [False, False]


def test_fuzzy_sent_to_cross_encoder(tmp_path):
    """fuzzy candidates are scored by the cross-encoder."""
    cfg = _make_cfg(tmp_path)
    candidates = pl.DataFrame({
        "post_id": [4],
        "attacker_id": ["ATK-001"],
        "match_type": ["fuzzy"],
        "alias_matched": ["alice"],
    })
    posts = _make_posts()
    cases = _make_cases()

    mock_model = MagicMock()
    mock_model.predict.return_value = np.array([2.0])  # sigmoid(2) ≈ 0.88 → accept

    with patch("saints_score.mentions.adjudicate._get_cross_encoder", return_value=mock_model):
        result = adjudicate_candidates(candidates, posts, cases, cfg)

    mock_model.predict.assert_called_once()
    assert result.height == 1
    assert result["is_reference"][0] is True
    assert result["confidence"][0] == pytest.approx(_sigmoid(np.array([2.0]))[0])


def test_fuzzy_below_threshold_rejected(tmp_path):
    """fuzzy candidate with low cross-encoder score is rejected."""
    cfg = _make_cfg(tmp_path)
    candidates = pl.DataFrame({
        "post_id": [2],
        "attacker_id": ["ATK-001"],
        "match_type": ["fuzzy"],
        "alias_matched": [""],
    })
    posts = _make_posts()
    cases = _make_cases()

    mock_model = MagicMock()
    mock_model.predict.return_value = np.array([-3.0])  # sigmoid(-3) ≈ 0.047 → reject

    with patch("saints_score.mentions.adjudicate._get_cross_encoder", return_value=mock_model):
        result = adjudicate_candidates(candidates, posts, cases, cfg)

    assert result.height == 1
    assert result["is_reference"][0] is False


def test_semantic_marked_oblique(tmp_path):
    """semantic candidates get is_oblique=True."""
    cfg = _make_cfg(tmp_path)
    candidates = pl.DataFrame({
        "post_id": [1],
        "attacker_id": ["ATK-001"],
        "match_type": ["semantic"],
        "alias_matched": [""],
    })
    posts = _make_posts()
    cases = _make_cases()

    mock_model = MagicMock()
    mock_model.predict.return_value = np.array([5.0])  # high confidence

    with patch("saints_score.mentions.adjudicate._get_cross_encoder", return_value=mock_model):
        result = adjudicate_candidates(candidates, posts, cases, cfg)

    assert result["is_oblique"][0] is True


def test_phonetic_skeleton_marked_oblique(tmp_path):
    """phonetic_skeleton candidates get is_oblique=True."""
    cfg = _make_cfg(tmp_path)
    candidates = pl.DataFrame({
        "post_id": [1],
        "attacker_id": ["ATK-001"],
        "match_type": ["phonetic_skeleton"],
        "alias_matched": [""],
    })
    posts = _make_posts()
    cases = _make_cases()

    mock_model = MagicMock()
    mock_model.predict.return_value = np.array([5.0])

    with patch("saints_score.mentions.adjudicate._get_cross_encoder", return_value=mock_model):
        result = adjudicate_candidates(candidates, posts, cases, cfg)

    assert result["is_oblique"][0] is True


def test_missing_post_text_rejected(tmp_path):
    """Candidates with no post text are rejected without model call."""
    cfg = _make_cfg(tmp_path)
    candidates = pl.DataFrame({
        "post_id": [999],  # no such post in posts
        "attacker_id": ["ATK-001"],
        "match_type": ["fuzzy"],
        "alias_matched": [""],
    })
    posts = _make_posts()
    cases = _make_cases()

    mock_model = MagicMock()
    mock_model.predict.return_value = np.array([])

    with patch("saints_score.mentions.adjudicate._get_cross_encoder", return_value=mock_model):
        result = adjudicate_candidates(candidates, posts, cases, cfg)

    mock_model.predict.assert_not_called()
    assert result.height == 1
    assert result["is_reference"][0] is False
    assert result["confidence"][0] == 0.0


def test_cache_persisted_and_reused(tmp_path):
    """Scored pairs are written to parquet cache and reused on second call."""
    cfg = _make_cfg(tmp_path)
    candidates = pl.DataFrame({
        "post_id": [3],
        "attacker_id": ["ATK-002"],
        "match_type": ["fuzzy"],
        "alias_matched": ["bob"],
    })
    posts = _make_posts()
    cases = _make_cases()

    mock_model = MagicMock()
    mock_model.predict.return_value = np.array([1.0])

    with patch("saints_score.mentions.adjudicate._get_cross_encoder", return_value=mock_model):
        adjudicate_candidates(candidates, posts, cases, cfg)
        # Second call should use cache, not model.predict
        adjudicate_candidates(candidates, posts, cases, cfg)

    # predict called exactly once (second call hits cache)
    assert mock_model.predict.call_count == 1


def test_max_candidates_cap(tmp_path):
    """max_candidates kwarg limits rows processed."""
    cfg = _make_cfg(tmp_path)
    candidates = pl.DataFrame({
        "post_id": [1, 2, 3],
        "attacker_id": ["ATK-001", "ATK-001", "ATK-001"],
        "match_type": ["exact_substring", "exact_substring", "exact_substring"],
        "alias_matched": ["a", "b", "c"],
    })
    posts = _make_posts()
    cases = _make_cases()

    result = adjudicate_candidates(candidates, posts, cases, cfg, max_candidates=2)
    assert result.height == 2


# ── filter_mentions ───────────────────────────────────────────────────────


def test_filter_mentions_threshold(tmp_path):
    cfg = _make_cfg(tmp_path)
    adjudicated = pl.DataFrame({
        "post_id": [1, 2, 3],
        "attacker_id": ["ATK-001", "ATK-001", "ATK-002"],
        "is_reference": [True, True, False],
        "confidence": [1.0, 0.3, 0.9],
        "inferred_alias": [None, None, None],
        "is_oblique": [False, False, False],
        "source_stage": ["exact_substring", "fuzzy", "fuzzy"],
        "alias_matched": ["", "", ""],
    })
    result = filter_mentions(adjudicated, cfg)
    # post 2: is_reference=True but confidence=0.3 < 0.5 → excluded
    # post 3: confidence=0.9 but is_reference=False → excluded
    assert result.height == 1
    assert result["post_id"][0] == 1


def test_filter_mentions_empty(tmp_path):
    cfg = _make_cfg(tmp_path)
    adjudicated = pl.DataFrame({
        "post_id": pl.Series([], dtype=pl.Int64),
        "attacker_id": pl.Series([], dtype=pl.Utf8),
        "is_reference": pl.Series([], dtype=pl.Boolean),
        "confidence": pl.Series([], dtype=pl.Float64),
        "inferred_alias": pl.Series([], dtype=pl.Utf8),
        "is_oblique": pl.Series([], dtype=pl.Boolean),
        "source_stage": pl.Series([], dtype=pl.Utf8),
        "alias_matched": pl.Series([], dtype=pl.Utf8),
    })
    result = filter_mentions(adjudicated, cfg)
    assert result.height == 0
