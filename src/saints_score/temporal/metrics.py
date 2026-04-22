"""Temporal metrics: intensity, longevity, and decay fitting (§6.4).

Computes per-attacker temporal dynamics from mention counts.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any

import numpy as np
import polars as pl
from scipy import optimize

from saints_score.io.parquet import write_parquet
from saints_score.logging import logger

if TYPE_CHECKING:
    from saints_score.config import Settings


def compute_daily_counts(
    mentions: pl.DataFrame,
    posts: pl.DataFrame,
) -> pl.DataFrame:
    """Compute daily mention counts per attacker.

    Returns DataFrame: ``attacker_id``, ``date``, ``mention_count``, ``total_posts``.
    """
    # Join to get timestamps
    mention_with_ts = mentions.join(
        posts.select(["post_id", "timestamp_utc"]),
        on="post_id",
    )

    # Extract date
    mention_with_ts = mention_with_ts.with_columns(pl.col("timestamp_utc").dt.date().alias("date"))

    # Daily mention counts per attacker
    daily = (
        mention_with_ts.group_by(["attacker_id", "date"])
        .agg(pl.len().alias("mention_count"))
        .sort(["attacker_id", "date"])
    )

    # Total daily posts (for normalisation)
    total_daily = (
        posts.with_columns(pl.col("timestamp_utc").dt.date().alias("date"))
        .group_by("date")
        .agg(pl.len().alias("total_posts"))
    )

    daily = daily.join(total_daily, on="date", how="left")
    return daily


def compute_intensity(
    daily_counts: pl.DataFrame,
    cases: pl.DataFrame,
    cfg: Settings,
) -> pl.DataFrame:
    """Compute intensity I_a: mention proportion in the immediate window.

    I_a = mentions_a[t, t+7d] / total_posts[t, t+7d]
    """
    results: list[dict[str, Any]] = []

    for row in cases.iter_rows(named=True):
        case_id = row["case_id"]
        event_date = row.get("event_date")
        if event_date is None:
            continue

        from datetime import date as date_type

        if isinstance(event_date, str):
            event_date = date_type.fromisoformat(event_date)

        window_start = event_date + timedelta(days=cfg.immediate_start)
        window_end = event_date + timedelta(days=cfg.immediate_end)

        window_data = daily_counts.filter(
            (pl.col("attacker_id") == case_id)
            & (pl.col("date") >= window_start)
            & (pl.col("date") <= window_end)
        )

        mentions_sum = window_data.select(pl.col("mention_count").sum()).item()
        total_sum = window_data.select(pl.col("total_posts").sum()).item()

        intensity = mentions_sum / total_sum if total_sum > 0 else 0.0

        results.append(
            {
                "attacker_id": case_id,
                "intensity": intensity,
                "mentions_immediate": int(mentions_sum),
                "total_posts_immediate": int(total_sum),
            }
        )

    return pl.DataFrame(results)


def _power_law(tau: np.ndarray, C: float, alpha: float) -> np.ndarray:
    """Power law decay: m(tau) = C * tau^(-alpha)."""
    return C * np.power(tau, -alpha)


def fit_decay(
    daily_counts: pl.DataFrame,
    cases: pl.DataFrame,
    cfg: Settings,
) -> pl.DataFrame:
    """Fit power-law decay to daily mention counts.

    L_a = 1 / alpha_a  (higher = slower decay = stickier).
    """
    results: list[dict[str, Any]] = []

    for row in cases.iter_rows(named=True):
        case_id = row["case_id"]
        event_date = row.get("event_date")
        if event_date is None:
            continue

        from datetime import date as date_type

        if isinstance(event_date, str):
            event_date = date_type.fromisoformat(event_date)

        # Get mention data for this attacker post-attack
        atk_data = daily_counts.filter(
            (pl.col("attacker_id") == case_id) & (pl.col("date") > event_date)
        )

        if atk_data.height < 5:
            results.append(
                {
                    "attacker_id": case_id,
                    "longevity": None,
                    "alpha": None,
                    "alpha_se": None,
                    "C": None,
                    "n_days": atk_data.height,
                    "fit_success": False,
                }
            )
            continue

        # Compute days since attack
        dates = atk_data.select("date").to_series().to_list()
        counts = atk_data.select("mention_count").to_series().to_list()

        tau = np.array([(d - event_date).days for d in dates], dtype=float)
        y = np.array(counts, dtype=float)

        # Filter to positive tau and y
        mask = (tau > 0) & (y > 0)
        tau = tau[mask]
        y = y[mask]

        if len(tau) < 5:
            results.append(
                {
                    "attacker_id": case_id,
                    "longevity": None,
                    "alpha": None,
                    "alpha_se": None,
                    "C": None,
                    "n_days": len(tau),
                    "fit_success": False,
                }
            )
            continue

        # Cap to longterm window
        keep = tau <= cfg.longterm_end
        tau = tau[keep]
        y = y[keep]

        if len(tau) < 3:
            results.append(
                {
                    "attacker_id": case_id,
                    "longevity": None,
                    "alpha": None,
                    "alpha_se": None,
                    "C": None,
                    "n_days": len(tau),
                    "fit_success": False,
                }
            )
            continue

        try:
            popt, pcov = optimize.curve_fit(
                _power_law,
                tau,
                y,
                p0=[y[0], 1.0],
                bounds=([0, 0.01], [np.inf, 10.0]),
                maxfev=5000,
            )
            C_fit, alpha_fit = popt
            alpha_se = float(np.sqrt(np.diag(pcov))[1]) if pcov is not None else None
            longevity = 1.0 / alpha_fit if alpha_fit > 0 else None

            results.append(
                {
                    "attacker_id": case_id,
                    "longevity": longevity,
                    "alpha": alpha_fit,
                    "alpha_se": alpha_se,
                    "C": C_fit,
                    "n_days": len(tau),
                    "fit_success": True,
                }
            )
        except (RuntimeError, ValueError) as e:
            logger.warning("Decay fit failed for {}: {}", case_id, e)
            results.append(
                {
                    "attacker_id": case_id,
                    "longevity": None,
                    "alpha": None,
                    "alpha_se": None,
                    "C": None,
                    "n_days": len(tau),
                    "fit_success": False,
                }
            )

    return pl.DataFrame(results)


def compute_temporal_metrics(
    mentions: pl.DataFrame,
    posts: pl.DataFrame,
    cases: pl.DataFrame,
    cfg: Settings,
) -> pl.DataFrame:
    """Full Phase 4 pipeline: compute all temporal metrics.

    Returns combined DataFrame and writes to disk.
    """
    daily = compute_daily_counts(mentions, posts)
    intensity = compute_intensity(daily, cases, cfg)
    decay = fit_decay(daily, cases, cfg)

    temporal = intensity.join(decay, on="attacker_id", how="outer_coalesce")

    out_path = cfg.resolve(cfg.data_processed) / "temporal_metrics.parquet"
    write_parquet(temporal, out_path)

    logger.info("Temporal metrics: {} attackers", temporal.height)
    return temporal
