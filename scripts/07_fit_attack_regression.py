#!/usr/bin/env python
"""Phase 7 — Fit attack-characteristic regression.

Usage:
    python scripts/07_fit_attack_regression.py --config config.toml
"""

from __future__ import annotations

import click
import polars as pl

from saints_score.config import get_settings
from saints_score.io.parquet import read_parquet
from saints_score.io.run_log import RunLog
from saints_score.logging import logger, setup_logging


@click.command()
@click.option("--config", "config_path", type=click.Path(exists=True), default="config.toml")
@click.option("--dry-run", is_flag=True)
@click.option("--limit", type=int, default=None)
def main(config_path: str, dry_run: bool, limit: int | None) -> None:
    """Phase 7: Fit hierarchical Bayesian regression."""
    cfg = get_settings(config_path)
    run = RunLog(phase="07_regression", config=cfg.model_dump(mode="json"))

    setup_logging(
        log_file=cfg.runs / "07_regression" / "stdout.log" if not dry_run else None,
    )

    # Load scores + cases
    scores_path = cfg.resolve(cfg.out_dir) / "scores" / "saints_bayes.csv"
    if not scores_path.exists():
        logger.error("Bayesian scores not found. Run Phase 6 first.")
        return

    saints = pl.read_csv(scores_path)
    cases = read_parquet(cfg.resolve(cfg.data_processed) / "cases.parquet")

    from saints_score.models.regression import fit_regression, prepare_regression_data

    data = prepare_regression_data(saints, cases)
    logger.info("Regression data: {} observations", data.height)

    if dry_run:
        logger.info("Dry run — skipping model fitting.")
        return

    _trace, coef_df = fit_regression(data, cfg)

    # Forest plot
    from saints_score.viz.plots import plot_regression_forest

    fig_dir = cfg.resolve(cfg.out_dir) / "figures"
    plot_regression_forest(coef_df, fig_dir)

    run.metrics = {
        "n_observations": data.height,
        "n_predictors": coef_df.height,
    }

    summary_dir = run.save(cfg.runs)
    (summary_dir / "SUMMARY.md").write_text(
        f"# Phase 7 — Regression Summary\n\n"
        f"- Observations: {data.height}\n"
        f"- Predictors: {coef_df.height}\n"
        f"- Model saved to out/models/attack_regression.nc\n"
        f"- Coefficient table: out/tables/regression_coefficients.csv\n",
        encoding="utf-8",
    )

    logger.info("Phase 7 complete. Review PPC + LOO diagnostics.")


if __name__ == "__main__":
    main()
