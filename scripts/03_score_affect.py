#!/usr/bin/env python
"""Phase 3 — Affective classification (sentiment, emotion, toxicity).

Usage:
    python scripts/03_score_affect.py --config config.toml
"""

from __future__ import annotations

import click
import polars as pl

from saints_score.config import get_settings
from saints_score.io.parquet import read_parquet, scan_partitioned
from saints_score.io.run_log import RunLog
from saints_score.logging import logger, setup_logging


@click.command()
@click.option("--config", "config_path", type=click.Path(exists=True), default="config.toml")
@click.option("--dry-run", is_flag=True)
@click.option("--limit", type=int, default=None, help="Limit posts for testing.")
def main(config_path: str, dry_run: bool, limit: int | None) -> None:
    """Phase 3: Score affect on mention posts."""
    cfg = get_settings(config_path)
    run = RunLog(phase="03_affect", config=cfg.model_dump(mode="json"))

    setup_logging(
        log_file=cfg.runs / "03_affect" / "stdout.log" if not dry_run else None,
    )

    # ── Load mentions ──
    mentions_path = cfg.resolve(cfg.data_processed) / "mentions.parquet"
    if not mentions_path.exists():
        logger.error("Mentions not found. Run Phase 2 first.")
        return
    mentions = read_parquet(mentions_path)
    logger.info("Loaded {} mentions", mentions.height)

    # ── Load posts ──
    posts_lf = scan_partitioned(cfg.pol_parquet)
    mention_pids = mentions.select("post_id").unique()
    posts = posts_lf.filter(pl.col("post_id").is_in(mention_pids["post_id"])).collect()
    logger.info("Loaded {} mention posts", posts.height)

    if limit:
        posts = posts.head(limit)
        mentions = mentions.filter(pl.col("post_id").is_in(posts["post_id"]))

    # ── Run affect pipeline ──
    from saints_score.affect.classify import run_affect_pipeline
    affect = run_affect_pipeline(mentions, posts, cfg)

    run.metrics = {
        "n_posts_scored": affect.height,
        "columns": affect.columns,
    }

    if not dry_run:
        run.hash_output(cfg.resolve(cfg.data_processed) / "affect_scores.parquet")
        summary_dir = run.save(cfg.runs)
        (summary_dir / "SUMMARY.md").write_text(
            f"# Phase 3 — Affect Scoring Summary\n\n"
            f"- Posts scored: {affect.height}\n"
            f"- Columns: {len(affect.columns)}\n",
            encoding="utf-8",
        )

    logger.info("Phase 3 complete. Awaiting domain-validity review.")


if __name__ == "__main__":
    main()
