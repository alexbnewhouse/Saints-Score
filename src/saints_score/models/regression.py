"""Hierarchical Bayesian regression of Saints Score on attack characteristics (§6.7).

DV: posterior-mean Saints Score (Bayesian).
IVs: ideology, weapon, manifesto, livestream, target type, log(casualties), demographics.
Partial pooling on ideology and country.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import arviz as az
import numpy as np
import polars as pl
import pymc as pm

from saints_score.logging import logger

if TYPE_CHECKING:
    from saints_score.config import Settings


def prepare_regression_data(
    saints_scores: pl.DataFrame,
    cases: pl.DataFrame,
) -> pl.DataFrame:
    """Merge Saints Scores with case metadata for regression.

    Returns a clean DataFrame with no nulls in required columns.
    """
    # Join on attacker_id = case_id
    merged = saints_scores.join(
        cases,
        left_on="attacker_id",
        right_on="case_id",
        how="inner",
    )

    # Compute log casualties
    if "fatalities_excl_perp" in merged.columns:
        merged = merged.with_columns(
            (pl.col("fatalities_excl_perp").cast(pl.Float64) + 1.0).log().alias("log_casualties")
        )

    # Binary dummies
    for col in ["manifesto_exists", "livestream_successful"]:
        if col in merged.columns:
            merged = merged.with_columns((pl.col(col) == "Y").cast(pl.Int8).alias(f"{col}_bin"))

    return merged


def fit_regression(
    data: pl.DataFrame,
    cfg: Settings,
    *,
    n_samples: int = 2000,
    n_tune: int = 1000,
) -> tuple[az.InferenceData, pl.DataFrame]:
    """Fit hierarchical Bayesian regression.

    Returns (InferenceData, coefficient_summary DataFrame).
    """
    logger.info("Preparing regression with {} observations", data.height)

    y = data["saints_bayes_mean"].to_numpy()
    N = len(y)

    # Encode categoricals
    ideology_vals = (
        data.get_column("saints_tradition").to_list()
        if "saints_tradition" in data.columns
        else ["none"] * N
    )
    unique_ideologies = sorted(set(ideology_vals))
    ideology_idx = np.array(
        [unique_ideologies.index(v) if v in unique_ideologies else 0 for v in ideology_vals]
    )
    n_ideology = len(unique_ideologies)

    country_vals = (
        data.get_column("country").to_list() if "country" in data.columns else ["unknown"] * N
    )
    unique_countries = sorted(set(country_vals))
    country_idx = np.array(
        [unique_countries.index(v) if v in unique_countries else 0 for v in country_vals]
    )
    n_country = len(unique_countries)

    # Continuous / binary predictors
    X_cols = []
    X_data = []

    for col in ["log_casualties", "manifesto_exists_bin", "livestream_successful_bin"]:
        if col in data.columns:
            vals = data[col].fill_null(0).to_numpy().astype(float)
            X_data.append(vals)
            X_cols.append(col)

    if "perp_age" in data.columns:
        age = data["perp_age"].fill_null(data["perp_age"].median()).to_numpy().astype(float)
        age_std = (age - age.mean()) / (age.std() + 1e-8)
        X_data.append(age_std)
        X_cols.append("perp_age_std")

    X = np.column_stack(X_data) if X_data else np.zeros((N, 1))
    n_predictors = X.shape[1]

    logger.info(
        "Regression: {} obs, {} predictors, {} ideologies, {} countries",
        N,
        n_predictors,
        n_ideology,
        n_country,
    )

    with pm.Model():
        # Priors
        intercept = pm.Normal("intercept", mu=0, sigma=1)
        beta = pm.Normal("beta", mu=0, sigma=1, shape=n_predictors)

        # Partial pooling on ideology
        sigma_ideology = pm.HalfNormal("sigma_ideology", sigma=0.5)
        alpha_ideology = pm.Normal("alpha_ideology", mu=0, sigma=sigma_ideology, shape=n_ideology)

        # Partial pooling on country
        sigma_country = pm.HalfNormal("sigma_country", sigma=0.5)
        alpha_country = pm.Normal("alpha_country", mu=0, sigma=sigma_country, shape=n_country)

        # Residual
        sigma = pm.HalfNormal("sigma", sigma=1)

        # Linear predictor
        mu = (
            intercept
            + pm.math.dot(X, beta)
            + alpha_ideology[ideology_idx]
            + alpha_country[country_idx]
        )

        # Likelihood
        pm.Normal("y", mu=mu, sigma=sigma, observed=y)

        # Sample
        trace = pm.sample(
            draws=n_samples,
            tune=n_tune,
            random_seed=cfg.seed,
            return_inferencedata=True,
            progressbar=True,
        )

    # Summary table
    summary = az.summary(trace, var_names=["intercept", "beta", "sigma"], hdi_prob=0.89)
    logger.info("Regression summary:\n{}", summary)

    # Create labelled coefficient table
    beta_summary = az.summary(trace, var_names=["beta"], hdi_prob=0.89)
    beta_summary.index = X_cols

    coef_df = pl.from_pandas(beta_summary.reset_index().rename(columns={"index": "predictor"}))

    # Save
    out_table = cfg.resolve(cfg.out_dir) / "tables" / "regression_coefficients.csv"
    out_table.parent.mkdir(parents=True, exist_ok=True)
    coef_df.write_csv(out_table)

    nc_path = cfg.resolve(cfg.out_dir) / "models" / "attack_regression.nc"
    nc_path.parent.mkdir(parents=True, exist_ok=True)
    trace.to_netcdf(str(nc_path))

    return trace, coef_df
