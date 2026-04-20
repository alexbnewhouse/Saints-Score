"""Tests for saints_score.semantic.drift — embedding-space drift analysis."""

from datetime import UTC, datetime

import numpy as np
import polars as pl

from saints_score.semantic.drift import (
    _compute_window_stats,
    _cosine_distance,
    compute_drift_summary,
)


# ── _cosine_distance ───────────────────────────────────────────────

def test_cosine_distance_identical():
    a = np.array([1.0, 0.0, 0.0])
    assert abs(_cosine_distance(a, a)) < 1e-6


def test_cosine_distance_orthogonal():
    a = np.array([1.0, 0.0])
    b = np.array([0.0, 1.0])
    assert abs(_cosine_distance(a, b) - 1.0) < 1e-6


def test_cosine_distance_opposite():
    a = np.array([1.0, 0.0])
    b = np.array([-1.0, 0.0])
    assert abs(_cosine_distance(a, b) - 2.0) < 1e-6


# ── _compute_window_stats ──────────────────────────────────────────

def test_window_stats_single_embedding():
    emb = np.array([[1.0, 0.0, 0.0]])
    stats = _compute_window_stats(emb)
    assert stats["centroid_norm"] > 0
    assert stats["mean_dispersion"] == 0.0
    assert stats["n_posts"] == 1


def test_window_stats_multiple():
    rng = np.random.default_rng(42)
    emb = rng.random((20, 3))
    # Normalise
    norms = np.linalg.norm(emb, axis=1, keepdims=True)
    emb = emb / norms
    stats = _compute_window_stats(emb)
    assert stats["n_posts"] == 20
    assert 0.0 <= stats["mean_dispersion"] <= 2.0  # cosine distance range


def test_window_stats_empty():
    emb = np.zeros((0, 3))
    stats = _compute_window_stats(emb)
    assert stats["n_posts"] == 0
    assert stats["centroid_norm"] == 0.0


# ── compute_drift_summary ──────────────────────────────────────────

def test_drift_summary_schema():
    """Summary should have the expected columns."""
    df = pl.DataFrame(
        {
            "attacker_id": ["A", "A", "A"],
            "window_start": [
                datetime(2019, 3, 15, tzinfo=UTC),
                datetime(2019, 3, 22, tzinfo=UTC),
                datetime(2019, 3, 29, tzinfo=UTC),
            ],
            "window_end": [
                datetime(2019, 3, 22, tzinfo=UTC),
                datetime(2019, 3, 29, tzinfo=UTC),
                datetime(2019, 4, 5, tzinfo=UTC),
            ],
            "centroid_drift": [0.0, 0.1, 0.15],
            "dispersion": [0.3, 0.35, 0.4],
            "evasion_rate": [0.0, 0.1, 0.2],
            "cumulative_drift": [0.0, 0.1, 0.25],
            "n_posts": [50, 30, 20],
        }
    )
    summary = compute_drift_summary(df)
    assert summary.height == 1
    assert "attacker_id" in summary.columns
    assert "mean_drift" in summary.columns
    assert "max_drift" in summary.columns
    assert "dispersion_trend" in summary.columns
    assert "mean_evasion_rate" in summary.columns


def test_drift_summary_multiple_attackers():
    """Summary should produce one row per attacker."""
    rows = []
    for aid in ["A", "B"]:
        for i in range(3):
            rows.append({
                "attacker_id": aid,
                "window_start": datetime(2019, 3, 1 + i * 7, tzinfo=UTC),
                "window_end": datetime(2019, 3, 8 + i * 7, tzinfo=UTC),
                "centroid_drift": 0.05 * (i + 1),
                "dispersion": 0.3 + 0.02 * i,
                "evasion_rate": 0.1 * i,
                "cumulative_drift": 0.05 * (i + 1),
                "n_posts": 50 - 10 * i,
            })
    df = pl.DataFrame(rows)
    summary = compute_drift_summary(df)
    assert summary.height == 2
