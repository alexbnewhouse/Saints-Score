"""Composite Saints Score computation (§6.6).

Two versions:
1. Naïve: scaled components with log-ratio, single scalar per attacker.
2. Bayesian: one-factor confirmatory model in PyMC.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import polars as pl

from saints_score.logging import logger

if TYPE_CHECKING:
    from saints_score.config import Settings

# ── Naïve Saints Score ───────────────────────────────────────────────────

def _min_max_scale(series: pl.Series) -> pl.Series:
    """Min-max scale a series to [0, 1]."""
    mn = series.min()
    mx = series.max()
    if mn == mx:
        return pl.Series(series.name, [0.5] * len(series))
    return (series - mn) / (mx - mn)


def compute_naive_score(
    affect: pl.DataFrame,
    temporal: pl.DataFrame,
    semantic: pl.DataFrame,
    mentions: pl.DataFrame,
    cfg: Settings,
) -> pl.DataFrame:
    """Compute the naïve Saints Score per attacker.

    Saints_a = log((E+ + eps) / (E- + eps)) z-scored × (I_scaled + L_scaled + S_scaled)
    """
    eps = cfg.epsilon

    # Aggregate affect per attacker
    # We need positive/negative emotion ratio from affect + mentions
    affect_agg = _aggregate_affect(affect, mentions)

    # Build feature table
    features = affect_agg
    features = features.join(
        temporal.select(["attacker_id", "intensity", "longevity"]),
        on="attacker_id",
        how="outer_coalesce",
    )
    features = features.join(
        semantic.select(["attacker_id", "similarity_median"]),
        on="attacker_id",
        how="outer_coalesce",
    )

    # Fill nulls
    features = features.with_columns(
        pl.col("intensity").fill_null(0.0),
        pl.col("longevity").fill_null(0.0),
        pl.col("similarity_median").fill_null(0.0),
        pl.col("positive_ratio").fill_null(0.5),
        pl.col("negative_ratio").fill_null(0.5),
    )

    # Log ratio (z-scored)
    features = features.with_columns(
        (
            (pl.col("positive_ratio") + eps).log() - (pl.col("negative_ratio") + eps).log()
        ).alias("log_affect_ratio")
    )
    mean_lar = features.select(pl.col("log_affect_ratio").mean()).item()
    std_lar = features.select(pl.col("log_affect_ratio").std()).item()
    if std_lar and std_lar > 0:
        features = features.with_columns(
            ((pl.col("log_affect_ratio") - mean_lar) / std_lar).alias("log_affect_ratio_z")
        )
    else:
        features = features.with_columns(
            pl.lit(0.0).alias("log_affect_ratio_z")
        )

    # Min-max scale I, L, S
    I_scaled = _min_max_scale(features["intensity"])
    L_scaled = _min_max_scale(features["longevity"])
    S_scaled = _min_max_scale(features["similarity_median"])

    features = features.with_columns(
        I_scaled.alias("intensity_scaled"),
        L_scaled.alias("longevity_scaled"),
        S_scaled.alias("similarity_scaled"),
    )

    # Composite
    features = features.with_columns(
        (
            pl.col("log_affect_ratio_z")
            * (pl.col("intensity_scaled") + pl.col("longevity_scaled") + pl.col("similarity_scaled"))
        ).alias("saints_naive")
    )

    out_path = cfg.resolve(cfg.out_dir) / "scores" / "saints_naive.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    features.write_csv(out_path)
    logger.info("Naïve Saints Score → {}", out_path)

    return features


def _aggregate_affect(
    affect: pl.DataFrame,
    mentions: pl.DataFrame,
) -> pl.DataFrame:
    """Aggregate affect scores per attacker from per-post scores.

    Classifies sentiment labels into positive/negative buckets.
    """
    # Join affect with mentions to get attacker_id
    merged = mentions.select(["post_id", "attacker_id"]).join(
        affect.select(["post_id", "sentiment_label", "sentiment_score"]),
        on="post_id",
        how="inner",
    )

    # Count positive/negative per attacker
    pos_labels = {"positive"}
    neg_labels = {"negative"}

    agg = merged.group_by("attacker_id").agg(
        pl.col("sentiment_label").is_in(list(pos_labels)).sum().alias("n_positive"),
        pl.col("sentiment_label").is_in(list(neg_labels)).sum().alias("n_negative"),
        pl.count().alias("n_total"),
    )

    agg = agg.with_columns(
        (pl.col("n_positive") / pl.col("n_total")).alias("positive_ratio"),
        (pl.col("n_negative") / pl.col("n_total")).alias("negative_ratio"),
    )

    return agg


# ── Bayesian Saints Score ────────────────────────────────────────────────

def compute_bayesian_score(
    affect: pl.DataFrame,
    temporal: pl.DataFrame,
    semantic: pl.DataFrame,
    mentions: pl.DataFrame,
    cfg: Settings,
    *,
    n_samples: int = 2000,
    n_tune: int = 1000,
) -> pl.DataFrame:
    """Fit a one-factor confirmatory model in PyMC.

    Five indicators: log(E+/E-), I, L, S, log(mention volume).
    Returns posterior factor scores with 89% HDIs.
    """
    import arviz as az
    import pymc as pm

    # Build indicator matrix
    affect_agg = _aggregate_affect(affect, mentions)

    vol = (
        mentions.group_by("attacker_id")
        .agg(pl.count().alias("mention_volume"))
    )

    features = affect_agg.join(
        temporal.select(["attacker_id", "intensity", "longevity"]),
        on="attacker_id", how="outer_coalesce",
    ).join(
        semantic.select(["attacker_id", "similarity_median"]),
        on="attacker_id", how="outer_coalesce",
    ).join(vol, on="attacker_id", how="outer_coalesce")

    features = features.fill_null(0.0)

    eps = cfg.epsilon
    attackers = features["attacker_id"].to_list()
    N = len(attackers)

    log_ratio = np.log(
        (features["positive_ratio"].to_numpy() + eps)
        / (features["negative_ratio"].to_numpy() + eps)
    )
    intensity = features["intensity"].to_numpy()
    longevity = features["longevity"].to_numpy()
    similarity = features["similarity_median"].to_numpy()
    log_volume = np.log1p(features["mention_volume"].to_numpy())

    # Standardise
    def _standardise(x: np.ndarray) -> np.ndarray:
        s = x.std()
        return (x - x.mean()) / s if s > 0 else np.zeros_like(x)

    Y = np.column_stack([
        _standardise(log_ratio),
        _standardise(intensity),
        _standardise(longevity),
        _standardise(similarity),
        _standardise(log_volume),
    ])
    indicator_names = ["log_affect_ratio", "intensity", "longevity", "similarity", "log_volume"]

    logger.info("Fitting Bayesian factor model: {} attackers, {} indicators", N, Y.shape[1])

    with pm.Model():
        # Latent factor
        eta = pm.Normal("eta", mu=0, sigma=1, shape=N)

        # Loadings (weakly informative)
        lam = pm.Normal("lambda", mu=0.5, sigma=1, shape=Y.shape[1])

        # Residual std
        sigma = pm.HalfNormal("sigma", sigma=1, shape=Y.shape[1])

        # Likelihood
        for j in range(Y.shape[1]):
            pm.Normal(
                f"y_{indicator_names[j]}",
                mu=lam[j] * eta,
                sigma=sigma[j],
                observed=Y[:, j],
            )

        # Sample
        np.random.seed(cfg.seed)
        trace = pm.sample(
            draws=n_samples,
            tune=n_tune,
            random_seed=cfg.seed,
            return_inferencedata=True,
            progressbar=True,
        )

    # Extract factor scores
    eta_posterior = trace.posterior["eta"].values  # (chains, draws, N)
    eta_flat = eta_posterior.reshape(-1, N)  # (total_draws, N)

    means = eta_flat.mean(axis=0)
    hdi = az.hdi(trace, hdi_prob=0.89, var_names=["eta"])
    hdi_vals = hdi["eta"].values  # (N, 2)

    # Loadings summary
    lam_summary = az.summary(trace, var_names=["lambda"], hdi_prob=0.89)
    logger.info("Factor loadings:\n{}", lam_summary)

    result = pl.DataFrame({
        "attacker_id": attackers,
        "saints_bayes_mean": means,
        "saints_bayes_hdi_lo": hdi_vals[:, 0],
        "saints_bayes_hdi_hi": hdi_vals[:, 1],
    })

    out_path = cfg.resolve(cfg.out_dir) / "scores" / "saints_bayes.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result.write_csv(out_path)
    logger.info("Bayesian Saints Score → {}", out_path)

    # Save InferenceData
    nc_path = cfg.resolve(cfg.out_dir) / "models" / "saints_factor.nc"
    nc_path.parent.mkdir(parents=True, exist_ok=True)
    trace.to_netcdf(str(nc_path))

    return result
