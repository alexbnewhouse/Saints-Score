#!/usr/bin/env python
"""Phase 6 — Assemble composite Saints Score (naïve + Bayesian).

Usage:
    python scripts/06_assemble_saints_score.py --config config.toml
"""

from __future__ import annotations

import click

from saints_score.config import get_settings
from saints_score.io.parquet import read_parquet
from saints_score.io.run_log import RunLog
from saints_score.logging import logger, setup_logging


@click.command()
@click.option("--config", "config_path", type=click.Path(exists=True), default="config.toml")
@click.option("--dry-run", is_flag=True)
@click.option("--limit", type=int, default=None)
@click.option("--skip-bayes", is_flag=True, help="Skip Bayesian model (fast mode).")
def main(config_path: str, dry_run: bool, limit: int | None, skip_bayes: bool) -> None:
    """Phase 6: Compute composite Saints Score."""
    cfg = get_settings(config_path)
    run = RunLog(phase="06_scoring", config=cfg.model_dump(mode="json"))

    setup_logging(
        log_file=cfg.runs / "06_scoring" / "stdout.log" if not dry_run else None,
    )

    processed = cfg.resolve(cfg.data_processed)
    affect = read_parquet(processed / "affect_scores.parquet")
    temporal = read_parquet(processed / "temporal_metrics.parquet")
    semantic = read_parquet(processed / "semantic_metrics.parquet")
    mentions = read_parquet(processed / "mentions.parquet")

    # ── Naïve score ──
    from saints_score.scoring.composite import compute_naive_score

    naive = compute_naive_score(affect, temporal, semantic, mentions, cfg)
    logger.info("Naïve scores computed for {} attackers", naive.height)

    # ── Bayesian score ──
    bayes = None
    if not skip_bayes:
        from saints_score.scoring.composite import compute_bayesian_score

        bayes = compute_bayesian_score(affect, temporal, semantic, mentions, cfg)
        logger.info("Bayesian scores computed for {} attackers", bayes.height)

    # ── Comparison plot ──
    if bayes is not None and not dry_run:
        from saints_score.viz.plots import plot_saints_comparison

        fig_dir = cfg.resolve(cfg.out_dir) / "figures"
        plot_saints_comparison(naive, bayes, fig_dir)

    run.metrics = {
        "n_naive": naive.height,
        "n_bayes": bayes.height if bayes is not None else 0,
    }

    if not dry_run:
        summary_dir = run.save(cfg.runs)
        (summary_dir / "SUMMARY.md").write_text(
            f"# Phase 6 — Saints Score Assembly Summary\n\n"
            f"- Naïve scores: {naive.height} attackers\n"
            f"- Bayesian scores: {bayes.height if bayes is not None else 'skipped'}\n"
            f"- Face validity check: inspect top/bottom ranked attackers\n",
            encoding="utf-8",
        )

    logger.info("Phase 6 complete. Check face validity before Phase 7.")


if __name__ == "__main__":
    main()
