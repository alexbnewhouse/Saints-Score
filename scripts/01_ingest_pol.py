#!/usr/bin/env python
"""Phase 1 — Ingest and normalize /pol/ corpus + validate cases.

Usage:
    python scripts/01_ingest_pol.py --config config.toml
    python scripts/01_ingest_pol.py --config config.toml --limit 10000 --dry-run
    python scripts/01_ingest_pol.py --config config.toml --cases-only
"""

from __future__ import annotations

import json

import click

from saints_score.config import get_settings
from saints_score.io.run_log import RunLog
from saints_score.logging import logger, setup_logging


@click.command()
@click.option("--config", "config_path", type=click.Path(exists=True), default="config.toml")
@click.option("--dry-run", is_flag=True, help="Parse but do not write files.")
@click.option("--limit", type=int, default=None, help="Stop after N rows (smoke test).")
@click.option("--cases-only", is_flag=True, help="Only process the cases dataset.")
def main(config_path: str, dry_run: bool, limit: int | None, cases_only: bool) -> None:
    """Phase 1: Ingest /pol/ and validate cases."""
    cfg = get_settings(config_path)
    run = RunLog(phase="01_ingest", config=cfg.model_dump(mode="json"))

    setup_logging(
        log_file=cfg.runs / "01_ingest" / "stdout.log" if not dry_run else None,
    )

    # ── Cases ──
    logger.info("=== Processing case dataset ===")
    from saints_score.cases.loader import process_cases
    _cases_df, cases_report = process_cases(cfg)
    logger.info("Cases report: {}", json.dumps(cases_report, indent=2, default=str))

    if not dry_run:
        run.hash_output(cfg.resolve(cfg.data_processed) / "cases.parquet")

    if cases_only:
        run.metrics = cases_report
        if not dry_run:
            run.save(cfg.runs)
        return

    # ── /pol/ ingest ──
    logger.info("=== Ingesting /pol/ corpus ===")
    from saints_score.ingest.pol import ingest_pol

    if not cfg.pol_tar.exists():
        logger.error("/pol/ tar not found: {}. Skipping ingest.", cfg.pol_tar)
    else:
        if not dry_run:
            run.hash_input(cfg.pol_tar)
        manifest = ingest_pol(cfg, limit=limit, dry_run=dry_run)
        run.metrics = {**cases_report, "pol_manifest": manifest}
        logger.info("Ingest complete. Total rows: {}", manifest.get("total_rows", 0))

    # ── Summary ──
    if not dry_run:
        summary_dir = run.save(cfg.runs)
        summary_path = summary_dir / "SUMMARY.md"
        summary_path.write_text(
            f"# Phase 1 — Ingest Summary\n\n"
            f"- Cases: {cases_report['n_cases']} cases, {cases_report['n_columns']} columns\n"
            f"- /pol/ rows: {run.metrics.get('pol_manifest', {}).get('total_rows', 'N/A')}\n"
            f"- Dry run: {dry_run}\n"
            f"- Limit: {limit}\n",
            encoding="utf-8",
        )
        logger.info("Summary → {}", summary_path)

    logger.info("Phase 1 complete. Awaiting go/no-go for Phase 2.")


if __name__ == "__main__":
    main()
