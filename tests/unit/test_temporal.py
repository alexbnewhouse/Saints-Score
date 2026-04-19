"""Tests for saints_score.temporal.metrics — temporal metrics computation."""

from datetime import UTC, date, datetime

import numpy as np
import polars as pl

from saints_score.temporal.metrics import (
    _power_law,
    compute_daily_counts,
    compute_intensity,
)


def test_power_law():
    """Power law function C * tau^(-alpha) should match manual calculation."""
    tau = np.array([1.0, 2.0, 4.0])
    result = _power_law(tau, C=10.0, alpha=1.0)
    np.testing.assert_allclose(result, [10.0, 5.0, 2.5])


def test_power_law_zero_alpha():
    """Alpha=0 should give constant output."""
    tau = np.array([1.0, 10.0, 100.0])
    result = _power_law(tau, C=5.0, alpha=0.0)
    np.testing.assert_allclose(result, [5.0, 5.0, 5.0])


def test_compute_daily_counts():
    """Daily counts should aggregate mentions by attacker and date."""
    mentions = pl.DataFrame(
        {
            "post_id": [1, 2, 3],
            "attacker_id": ["A", "A", "B"],
        }
    )
    posts = pl.DataFrame(
        {
            "post_id": [1, 2, 3, 4],
            "timestamp_utc": [
                datetime(2019, 3, 15, 12, 0, tzinfo=UTC),
                datetime(2019, 3, 15, 18, 0, tzinfo=UTC),
                datetime(2019, 3, 16, 10, 0, tzinfo=UTC),
                datetime(2019, 3, 15, 14, 0, tzinfo=UTC),
            ],
        }
    )

    daily = compute_daily_counts(mentions, posts)
    assert daily.height >= 2

    # A should have 2 mentions on 2019-03-15
    a_march15 = daily.filter(
        (pl.col("attacker_id") == "A") & (pl.col("date") == date(2019, 3, 15))
    )
    assert a_march15.height == 1
    assert a_march15["mention_count"][0] == 2


def test_compute_intensity(cfg):
    """Intensity should equal mention proportion in immediate window."""
    daily_counts = pl.DataFrame(
        {
            "attacker_id": ["A", "A", "A"],
            "date": [date(2019, 3, 15), date(2019, 3, 16), date(2019, 3, 17)],
            "mention_count": [10, 5, 3],
            "total_posts": [100, 100, 100],
        }
    )
    cases = pl.DataFrame(
        {
            "case_id": ["A"],
            "event_date": [date(2019, 3, 15)],
        }
    )

    result = compute_intensity(daily_counts, cases, cfg)
    assert result.height == 1
    # Intensity = (10 + 5 + 3) / (100 + 100 + 100) = 18/300 = 0.06
    assert abs(result["intensity"][0] - 0.06) < 1e-6
