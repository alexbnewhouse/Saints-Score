#!/usr/bin/env python
"""Phase 5 — Semantic convergence.

Usage:
    python scripts/05_compute_semantic.py --config config.toml
"""

from __future__ import annotations

import click

from saints_score.config import get_settings
from saints_score.io.parquet import read_parquet, scan_partitioned
from saints_score.io.run_log import RunLog
from saints_score.logging import logger, setup_logging


@click.command()
@click.option("--config", "config_path", type=click.Path(exists=True), default="config.toml")
@click.option("--dry-run", is_flag=True)
@click.option("--limit", type=int, default=None)
def main(config_path: str, dry_run: bool, limit: int | None) -> None:
    """Phase 5: Compute semantic convergence metrics."""
    cfg = get_settings(config_path)
    run = RunLog(phase="05_semantic", config=cfg.model_dump(mode="json"))

    setup_logging(
        log_file=cfg.runs / "05_semantic" / "stdout.log" if not dry_run else None,
    )

    mentions = read_parquet(cfg.resolve(cfg.data_processed) / "mentions.parquet")
    cases = read_parquet(cfg.resolve(cfg.data_processed) / "cases.parquet")
    posts = scan_partitioned(cfg.pol_parquet).collect()

    if limit:
        mentions = mentions.head(limit)

    from saints_score.semantic.convergence import compute_semantic_metrics
    semantic = compute_semantic_metrics(mentions, posts, cases, cfg)

    run.metrics = {"n_attackers": semantic.height}

    if not dry_run:
        run.hash_output(cfg.resolve(cfg.data_processed) / "semantic_metrics.parquet")
        summary_dir = run.save(cfg.runs)
        (summary_dir / "SUMMARY.md").write_text(
            f"# Phase 5 — Semantic Convergence Summary\n\n"
            f"- Attackers scored: {semantic.height}\n",
            encoding="utf-8",
        )

    logger.info("Phase 5 complete. Inspect similarity distributions.")


if __name__ == "__main__":
    main()
