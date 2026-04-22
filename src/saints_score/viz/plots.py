"""Visualization helpers for the Saints Score pipeline.

Produces publication-quality figures for each pipeline phase.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import matplotlib.pyplot as plt
import numpy as np
import polars as pl

from saints_score.logging import logger

if TYPE_CHECKING:
    from pathlib import Path

# ── Style defaults ──────────────────────────────────────────────────────
plt.rcParams.update(
    {
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "font.size": 11,
        "axes.titlesize": 13,
        "axes.labelsize": 11,
    }
)


def _ensure_dir(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def plot_decay_curve(
    daily_counts: pl.DataFrame,
    attacker_id: str,
    event_date: Any,
    alpha: float | None,
    C: float | None,
    out_dir: Path,
) -> Path:
    """Plot mention decay curve for a single attacker."""
    atk = daily_counts.filter(pl.col("attacker_id") == attacker_id)
    if atk.height == 0:
        return out_dir

    from datetime import date as date_type

    if isinstance(event_date, str):
        event_date = date_type.fromisoformat(event_date)

    dates = atk["date"].to_list()
    counts = atk["mention_count"].to_list()
    days = [(d - event_date).days for d in dates]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.scatter(days, counts, s=8, alpha=0.5, label="Daily mentions")

    if alpha is not None and C is not None:
        tau = np.linspace(1, max(days) if days else 730, 200)
        fit = C * np.power(tau, -alpha)
        ax.plot(tau, fit, "r-", lw=2, label=f"Power law (α={alpha:.2f})")

    ax.set_xlabel("Days since attack")
    ax.set_ylabel("Daily mention count")
    ax.set_title(f"Mention decay: {attacker_id}")
    ax.legend()
    ax.set_xlim(left=0)

    out_path = _ensure_dir(out_dir / f"{attacker_id}.png")
    fig.savefig(out_path)
    plt.close(fig)
    return out_path


def plot_saints_comparison(
    naive_scores: pl.DataFrame,
    bayes_scores: pl.DataFrame,
    out_dir: Path,
) -> Path:
    """Scatter plot: naïve vs Bayesian Saints Score."""
    merged = naive_scores.select(["attacker_id", "saints_naive"]).join(
        bayes_scores.select(
            ["attacker_id", "saints_bayes_mean", "saints_bayes_hdi_lo", "saints_bayes_hdi_hi"]
        ),
        on="attacker_id",
    )

    fig, ax = plt.subplots(figsize=(8, 8))

    x = merged["saints_naive"].to_numpy()
    y = merged["saints_bayes_mean"].to_numpy()

    if len(x) == 0:
        logger.warning("No data to plot for saints comparison")
        plt.close(fig)
        return out_dir

    lo = merged["saints_bayes_hdi_lo"].to_numpy()
    hi = merged["saints_bayes_hdi_hi"].to_numpy()

    ax.errorbar(x, y, yerr=[y - lo, hi - y], fmt="o", capsize=3, alpha=0.7)

    # Label points
    for i, name in enumerate(merged["attacker_id"].to_list()):
        short = name.split("-")[-1] if "-" in name else name
        ax.annotate(
            short, (x[i], y[i]), fontsize=7, alpha=0.7, xytext=(3, 3), textcoords="offset points"
        )

    ax.set_xlabel("Naïve Saints Score")
    ax.set_ylabel("Bayesian Saints Score (mean ± 89% HDI)")
    ax.set_title("Saints Score: Naïve vs Bayesian")

    # 1:1 reference line
    lims = [min(x.min(), y.min()), max(x.max(), y.max())]
    ax.plot(lims, lims, "k--", alpha=0.3, label="1:1")
    ax.legend()

    out_path = _ensure_dir(out_dir / "saints_score_comparison.png")
    fig.savefig(out_path)
    plt.close(fig)
    logger.info("Saints comparison plot → {}", out_path)
    return out_path


def plot_regression_forest(
    coef_df: pl.DataFrame,
    out_dir: Path,
) -> Path:
    """Forest plot of regression coefficients with HDIs."""
    fig, ax = plt.subplots(figsize=(8, max(4, len(coef_df) * 0.4)))

    names = coef_df["predictor"].to_list()
    means = coef_df["mean"].to_numpy()

    # Try to find HDI columns
    hdi_lo_col = [c for c in coef_df.columns if "hdi_3%" in c.lower() or "hdi_5.5%" in c.lower()]
    hdi_hi_col = [c for c in coef_df.columns if "hdi_97%" in c.lower() or "hdi_94.5%" in c.lower()]

    y_pos = np.arange(len(names))

    if hdi_lo_col and hdi_hi_col:
        lo = coef_df[hdi_lo_col[0]].to_numpy()
        hi = coef_df[hdi_hi_col[0]].to_numpy()
        ax.errorbar(
            means, y_pos, xerr=[means - lo, hi - means], fmt="o", capsize=4, color="steelblue"
        )
    else:
        ax.scatter(means, y_pos, color="steelblue")

    ax.axvline(0, color="grey", linestyle="--", alpha=0.5)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(names)
    ax.set_xlabel("Coefficient (standardised)")
    ax.set_title("Attack Regression: Posterior Coefficients (89% HDI)")

    out_path = _ensure_dir(out_dir / "regression_forest.png")
    fig.savefig(out_path)
    plt.close(fig)
    logger.info("Regression forest plot → {}", out_path)
    return out_path
