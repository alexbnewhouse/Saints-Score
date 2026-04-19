"""Tests for saints_score.scoring.composite — naïve score computation."""

import polars as pl

from saints_score.scoring.composite import _min_max_scale


def test_min_max_scale():
    s = pl.Series("x", [0.0, 5.0, 10.0])
    scaled = _min_max_scale(s)
    assert scaled[0] == 0.0
    assert scaled[1] == 0.5
    assert scaled[2] == 1.0


def test_min_max_scale_constant():
    s = pl.Series("x", [5.0, 5.0, 5.0])
    scaled = _min_max_scale(s)
    assert all(v == 0.5 for v in scaled.to_list())
