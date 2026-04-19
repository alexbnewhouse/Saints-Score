"""Tests for saints_score.scoring.composite — affect aggregation."""

import polars as pl

from saints_score.scoring.composite import _aggregate_affect


def test_aggregate_affect_basic():
    """Positive/negative ratios are computed correctly."""
    mentions = pl.DataFrame(
        {
            "post_id": [1, 2, 3, 4],
            "attacker_id": ["A", "A", "A", "B"],
        }
    )
    affect = pl.DataFrame(
        {
            "post_id": [1, 2, 3, 4],
            "sentiment_label": ["positive", "negative", "positive", "negative"],
            "sentiment_score": [0.9, 0.8, 0.7, 0.95],
        }
    )

    result = _aggregate_affect(affect, mentions)
    assert result.height == 2

    a_row = result.filter(pl.col("attacker_id") == "A")
    assert a_row["n_positive"][0] == 2
    assert a_row["n_negative"][0] == 1
    assert a_row["n_total"][0] == 3
    assert abs(a_row["positive_ratio"][0] - 2 / 3) < 1e-6

    b_row = result.filter(pl.col("attacker_id") == "B")
    assert b_row["n_positive"][0] == 0
    assert b_row["n_negative"][0] == 1
    assert b_row["negative_ratio"][0] == 1.0


def test_aggregate_affect_neutral_excluded():
    """Neutral labels should not count as positive or negative."""
    mentions = pl.DataFrame(
        {
            "post_id": [1, 2],
            "attacker_id": ["A", "A"],
        }
    )
    affect = pl.DataFrame(
        {
            "post_id": [1, 2],
            "sentiment_label": ["neutral", "neutral"],
            "sentiment_score": [0.9, 0.8],
        }
    )

    result = _aggregate_affect(affect, mentions)
    assert result["n_positive"][0] == 0
    assert result["n_negative"][0] == 0
    assert result["n_total"][0] == 2
