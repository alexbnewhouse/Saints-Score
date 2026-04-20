"""Embedding-space drift analysis (§ new — ConTEXT-inspired).

Tracks how the embedding-space centroid of discourse about each attacker evolves
across temporal windows.  Inspired by:

- Rodriguez, Spirling & Stewart (2023). "Embedding Regression: Models for
  Context-Specific Description and Inference" (conText, APSR).
- Kutuzov et al. (2018). "Diachronic word embeddings and semantic shifts: a survey."
- Martinc et al. (2020). "Leveraging contextual embeddings for detecting diachronic
  semantic shift."
- Ali, Blackburn & Stringhini (2025). "Evolving hate speech online: an adaptive
  framework for detection and mitigation."

The core idea: compute per-attacker, per-time-window embedding centroids, then
measure:
1. **Centroid drift** — cosine distance between consecutive window centroids,
   capturing how discourse evolves (liturgical stabilisation vs drift).
2. **Dispersion trajectory** — how the intra-window spread changes over time
   (convergence = tighter community discourse = sainthood crystallisation).
3. **Adversarial evasion velocity** — rate of lexical/semantic innovation in oblique
   references, measured as the proportion of mentions landing far from the canonical
   centroid.
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

import numpy as np
import polars as pl

from saints_score.io.parquet import write_parquet
from saints_score.logging import logger
from saints_score.mentions.semantic import embed_texts

if TYPE_CHECKING:
    from saints_score.config import Settings


def _cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine distance between two vectors (1 - cosine_similarity)."""
    dot = float(np.dot(a, b))
    norm = float(np.linalg.norm(a) * np.linalg.norm(b))
    if norm < 1e-12:
        return 1.0
    return 1.0 - dot / norm


def _compute_window_stats(
    embeddings: np.ndarray,
) -> dict[str, float]:
    """Compute centroid, dispersion, and outlier stats for a set of embeddings."""
    n = embeddings.shape[0]
    if n == 0:
        return {
            "centroid_norm": 0.0,
            "mean_dispersion": 0.0,
            "std_dispersion": 0.0,
            "n_posts": 0,
        }

    centroid = embeddings.mean(axis=0)
    centroid_norm = float(np.linalg.norm(centroid))
    if centroid_norm > 0:
        centroid_unit = centroid / centroid_norm
    else:
        centroid_unit = centroid

    # Dispersion: mean cosine distance from centroid
    sims = embeddings @ centroid_unit
    distances = 1.0 - sims

    return {
        "centroid_norm": centroid_norm,
        "mean_dispersion": float(np.mean(distances)),
        "std_dispersion": float(np.std(distances)) if n > 1 else 0.0,
        "n_posts": n,
    }


def compute_drift_metrics(
    mentions: pl.DataFrame,
    posts: pl.DataFrame,
    cases: pl.DataFrame,
    cfg: Settings,
    *,
    window_days: int = 30,
    max_posts_per_window: int = 2000,
) -> pl.DataFrame:
    """Compute embedding-space drift metrics per attacker across time windows.

    For each attacker, divides the post-attack period into ``window_days``-wide
    windows, embeds the mention-set posts in each window, and tracks:
    - centroid_drift: cosine distance between consecutive window centroids
    - dispersion: mean cosine distance of posts from their window centroid
    - evasion_rate: fraction of posts with cosine distance > 2 * median distance
      from the canonical (first-window) centroid

    Parameters
    ----------
    mentions : pl.DataFrame
        Mention detection output with ``post_id``, ``attacker_id``.
    posts : pl.DataFrame
        Post corpus with ``post_id``, ``timestamp_utc``, ``body_clean``.
    cases : pl.DataFrame
        Case dataset with ``case_id``, ``event_date``.
    cfg : Settings
        Pipeline config.
    window_days : int
        Width of each temporal window in days.
    max_posts_per_window : int
        Cap posts per window for embedding efficiency.

    Returns
    -------
    pl.DataFrame with columns: attacker_id, window_start, window_end, n_posts,
    centroid_drift, dispersion, evasion_rate, cumulative_drift.
    """
    # Join mentions with post timestamps
    mention_posts = mentions.join(
        posts.select(["post_id", "timestamp_utc", "body_clean"]),
        on="post_id",
        how="inner",
    )

    results: list[dict[str, Any]] = []

    for case_row in cases.iter_rows(named=True):
        case_id = case_row["case_id"]
        event_date = case_row.get("event_date")
        if event_date is None:
            continue

        if isinstance(event_date, str):
            event_date = date.fromisoformat(event_date)

        atk_posts = mention_posts.filter(pl.col("attacker_id") == case_id)
        if atk_posts.height < 5:
            continue

        # Extract dates
        atk_posts = atk_posts.with_columns(
            pl.col("timestamp_utc").dt.date().alias("post_date"),
        )

        # Define windows
        min_date = event_date
        max_date = event_date + timedelta(days=cfg.longterm_end)

        windows: list[tuple[date, date]] = []
        w_start = min_date
        while w_start < max_date:
            w_end = w_start + timedelta(days=window_days)
            windows.append((w_start, w_end))
            w_start = w_end

        if not windows:
            continue

        # Track centroids across windows
        prev_centroid: np.ndarray | None = None
        canonical_centroid: np.ndarray | None = None
        canonical_median_dist: float = 0.0
        cumulative_drift: float = 0.0

        for w_start, w_end in windows:
            window_posts = atk_posts.filter(
                (pl.col("post_date") >= w_start) & (pl.col("post_date") < w_end)
            )

            if window_posts.height < 2:
                logger.debug(
                    "Skipping window {}-{} for {}: only {} posts",
                    w_start, w_end, case_id, window_posts.height,
                )
                continue

            # Sample if too many posts
            if window_posts.height > max_posts_per_window:
                window_posts = window_posts.sample(
                    n=max_posts_per_window, seed=cfg.seed,
                )

            texts = window_posts["body_clean"].to_list()
            embeddings = embed_texts(texts, cfg, show_progress=False)

            # Window stats
            stats = _compute_window_stats(embeddings)
            centroid = embeddings.mean(axis=0)
            c_norm = float(np.linalg.norm(centroid))
            if c_norm > 0:
                centroid = centroid / c_norm

            # Centroid drift from previous window
            drift = 0.0
            if prev_centroid is not None:
                drift = _cosine_distance(centroid, prev_centroid)
                cumulative_drift += drift

            # Canonical centroid (first window with enough data)
            if canonical_centroid is None:
                canonical_centroid = centroid.copy()
                sims_to_canonical = embeddings @ canonical_centroid
                canonical_median_dist = float(np.median(1.0 - sims_to_canonical))

            # Evasion rate: posts far from canonical centroid
            evasion_rate = 0.0
            if canonical_centroid is not None:
                sims = embeddings @ canonical_centroid
                dists = 1.0 - sims
                if canonical_median_dist > 1e-6:
                    threshold = 2.0 * canonical_median_dist
                else:
                    threshold = float(np.median(dists)) * 2.0 if len(dists) > 0 else 0.0
                if threshold > 0:
                    evasion_rate = float(np.mean(dists > threshold))

            results.append({
                "attacker_id": case_id,
                "window_start": w_start,
                "window_end": w_end,
                "n_posts": stats["n_posts"],
                "centroid_drift": drift,
                "dispersion": stats["mean_dispersion"],
                "dispersion_std": stats["std_dispersion"],
                "evasion_rate": evasion_rate,
                "cumulative_drift": cumulative_drift,
            })

            prev_centroid = centroid.copy()

    if not results:
        return pl.DataFrame(
            schema={
                "attacker_id": pl.Utf8,
                "window_start": pl.Date,
                "window_end": pl.Date,
                "n_posts": pl.Int64,
                "centroid_drift": pl.Float64,
                "dispersion": pl.Float64,
                "dispersion_std": pl.Float64,
                "evasion_rate": pl.Float64,
                "cumulative_drift": pl.Float64,
            }
        )

    df = pl.DataFrame(results)

    # Write
    out_path = cfg.resolve(cfg.data_processed) / "drift_metrics.parquet"
    write_parquet(df, out_path)

    logger.info(
        "Drift metrics: {} windows across {} attackers",
        df.height, df["attacker_id"].n_unique(),
    )
    return df


def compute_drift_summary(drift_df: pl.DataFrame) -> pl.DataFrame:
    """Aggregate drift metrics per attacker into summary statistics.

    Returns per-attacker: mean_drift, max_drift, final_cumulative_drift,
    mean_dispersion, dispersion_trend (slope), mean_evasion_rate.
    """
    results: list[dict[str, Any]] = []

    for attacker_id in drift_df["attacker_id"].unique().to_list():
        atk = drift_df.filter(pl.col("attacker_id") == attacker_id).sort("window_start")

        if atk.height < 2:
            continue

        drifts = atk["centroid_drift"].to_numpy()
        dispersions = atk["dispersion"].to_numpy()
        evasion = atk["evasion_rate"].to_numpy()

        # Dispersion trend: linear slope over time
        x = np.arange(len(dispersions), dtype=float)
        if len(x) > 1 and np.std(dispersions) > 0:
            slope = float(np.polyfit(x, dispersions, 1)[0])
        else:
            slope = 0.0

        results.append({
            "attacker_id": attacker_id,
            "mean_drift": float(np.mean(drifts)),
            "max_drift": float(np.max(drifts)),
            "final_cumulative_drift": float(atk["cumulative_drift"][-1]),
            "mean_dispersion": float(np.mean(dispersions)),
            "dispersion_trend": slope,  # negative = discourse converging
            "mean_evasion_rate": float(np.mean(evasion)),
            "n_windows": atk.height,
        })

    if not results:
        return pl.DataFrame(
            schema={
                "attacker_id": pl.Utf8,
                "mean_drift": pl.Float64,
                "max_drift": pl.Float64,
                "final_cumulative_drift": pl.Float64,
                "mean_dispersion": pl.Float64,
                "dispersion_trend": pl.Float64,
                "mean_evasion_rate": pl.Float64,
                "n_windows": pl.Int64,
            }
        )

    return pl.DataFrame(results)
