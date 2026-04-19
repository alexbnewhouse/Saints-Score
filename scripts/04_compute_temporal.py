#!/usr/bin/env python
"""Phase 4 — Temporal metrics (intensity, longevity, decay).

Usage:
    python scripts/04_compute_temporal.py --config config.toml
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
@click.option("--limit", type=int, default=None)
def main(config_path: str, dry_run: bool, limit: int | None) -> None:
    """Phase 4: Compute temporal metrics."""
    cfg = get_settings(config_path)
    run = RunLog(phase="04_temporal", config=cfg.model_dump(mode="json"))

    setup_logging(
        log_file=cfg.runs / "04_temporal" / "stdout.log" if not dry_run else None,
    )

    # ── Load data ──
    mentions = read_parquet(cfg.resolve(cfg.data_processed) / "mentions.parquet")
    cases = read_parquet(cfg.resolve(cfg.data_processed) / "cases.parquet")
    posts = scan_partitioned(cfg.pol_parquet).collect()

    if limit:
        mentions = mentions.head(limit)

    # ── Compute ──
    from saints_score.temporal.metrics import compute_daily_counts, compute_temporal_metrics

    temporal = compute_temporal_metrics(mentions, posts, cases, cfg)

    # ── Decay plots ──
    if not dry_run:
        from saints_score.viz.plots import plot_decay_curve

        daily = compute_daily_counts(mentions, posts)
        fig_dir = cfg.resolve(cfg.out_dir) / "figures" / "decay_per_attacker"
        for row in temporal.iter_rows(named=True):
            case_row = cases.filter(pl.col("case_id") == row["attacker_id"])
            if case_row.height > 0:
                event_date = case_row["event_date"][0]
                plot_decay_curve(
                    daily,
                    row["attacker_id"],
                    event_date,
                    row.get("alpha"),
                    row.get("C"),
                    fig_dir,
                )

    run.metrics = {
        "n_attackers": temporal.height,
        "fit_success_rate": temporal.filter(pl.col("fit_success")).height
        / max(temporal.height, 1),
    }

    if not dry_run:
        run.hash_output(cfg.resolve(cfg.data_processed) / "temporal_metrics.parquet")
        summary_dir = run.save(cfg.runs)
        (summary_dir / "SUMMARY.md").write_text(
            f"# Phase 4 — Temporal Metrics Summary\n\n"
            f"- Attackers: {temporal.height}\n"
            f"- Decay fit success rate: {run.metrics['fit_success_rate']:.1%}\n",
            encoding="utf-8",
        )

    logger.info("Phase 4 complete. Inspect decay fits per attacker.")


if __name__ == "__main__":
    main()
