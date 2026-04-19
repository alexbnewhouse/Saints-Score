#!/usr/bin/env python
"""Phase 2 — Attacker mention detection.

Multi-stage weak supervision: seed aliases → lexical retrieval → semantic
retrieval → LLM adjudication → alias bootstrapping.

Usage:
    python scripts/02_detect_mentions.py --config config.toml
    python scripts/02_detect_mentions.py --config config.toml --limit 1000 --dry-run
"""

from __future__ import annotations

import click

from saints_score.config import get_settings
from saints_score.io.parquet import read_parquet, scan_partitioned, write_parquet
from saints_score.io.run_log import RunLog
from saints_score.logging import logger, setup_logging


@click.command()
@click.option("--config", "config_path", type=click.Path(exists=True), default="config.toml")
@click.option("--dry-run", is_flag=True)
@click.option("--limit", type=int, default=None, help="Limit post count for testing.")
@click.option("--round", "bootstrap_round", type=int, default=1, help="Bootstrap iteration (1-3).")
def main(
    config_path: str,
    dry_run: bool,
    limit: int | None,
    bootstrap_round: int,
) -> None:
    """Phase 2: Detect attacker mentions."""
    cfg = get_settings(config_path)
    run = RunLog(phase="02_mentions", config=cfg.model_dump(mode="json"))

    setup_logging(
        log_file=cfg.runs / "02_mentions" / "stdout.log" if not dry_run else None,
    )

    # ── Load cases ──
    cases_path = cfg.resolve(cfg.data_processed) / "cases.parquet"
    if not cases_path.exists():
        logger.error("Cases not found at {}. Run Phase 1 first.", cases_path)
        return
    cases = read_parquet(cases_path)
    logger.info("Loaded {} cases", cases.height)

    # ── Load /pol/ posts ──
    pol_dir = cfg.pol_parquet
    if not pol_dir.exists():
        logger.error("/pol/ parquet dir not found: {}. Run Phase 1 first.", pol_dir)
        return
    posts_lf = scan_partitioned(pol_dir)
    if limit:
        posts_lf = posts_lf.head(limit)

    # ── Stage 1: Seed aliases ──
    logger.info("=== Stage 1: Building seed alias inventory ===")
    from saints_score.mentions.aliases import build_seed_aliases, save_seed_aliases

    aliases = build_seed_aliases(cases)
    if not dry_run:
        save_seed_aliases(aliases, cfg)

    # ── Stage 2: Lexical retrieval ──
    logger.info("=== Stage 2: Lexical candidate retrieval ===")
    from saints_score.mentions.lexical import lexical_candidate_retrieval

    lex_candidates = lexical_candidate_retrieval(posts_lf, aliases, cfg)
    logger.info("Lexical candidates: {}", lex_candidates.height)

    # ── Stage 3: Semantic retrieval ──
    logger.info("=== Stage 3: Semantic candidate retrieval ===")
    logger.info("(Skipping semantic retrieval in this run — requires embedding index)")
    # Full implementation would embed posts and run semantic_candidate_retrieval

    # ── Stage 4: LLM adjudication ──
    logger.info("=== Stage 4: LLM adjudication ===")
    posts_df = posts_lf.collect()
    from saints_score.mentions.adjudicate import adjudicate_candidates, filter_mentions

    adjudicated = adjudicate_candidates(
        lex_candidates,
        posts_df,
        cases,
        cfg,
        max_candidates=limit,
    )
    mentions = filter_mentions(adjudicated, cfg)

    # ── Output ──
    if not dry_run:
        mentions_path = cfg.resolve(cfg.data_processed) / "mentions.parquet"
        write_parquet(mentions, mentions_path)
        run.hash_output(mentions_path)

        aliases_path = cfg.resolve(cfg.data_processed) / "aliases_final.parquet"
        write_parquet(aliases, aliases_path)

    # ── Eval summary ──
    run.metrics = {
        "n_mentions": mentions.height,
        "n_attackers_with_mentions": mentions["attacker_id"].n_unique(),
        "n_lexical_candidates": lex_candidates.height,
        "bootstrap_round": bootstrap_round,
    }

    if not dry_run:
        summary_dir = run.save(cfg.runs)
        summary_path = summary_dir / "SUMMARY.md"
        summary_path.write_text(
            f"# Phase 2 — Mention Detection Summary\n\n"
            f"- Seed aliases: {aliases.height}\n"
            f"- Lexical candidates: {lex_candidates.height}\n"
            f"- Final mentions: {mentions.height}\n"
            f"- Attackers with mentions: {mentions['attacker_id'].n_unique()}\n"
            f"- Bootstrap round: {bootstrap_round}\n",
            encoding="utf-8",
        )

    logger.info("Phase 2 complete. Awaiting hand-coded validation for go/no-go.")


if __name__ == "__main__":
    main()
