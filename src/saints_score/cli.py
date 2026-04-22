"""Unified CLI entry point for the Saints Score pipeline.

Usage:
    python -m saints_score --help
    python -m saints_score ingest --config config.toml
    python -m saints_score mentions --config config.toml --limit 1000
    python -m saints_score affect --config config.toml
    python -m saints_score temporal --config config.toml
    python -m saints_score semantic --config config.toml
    python -m saints_score score --config config.toml
    python -m saints_score regression --config config.toml
    python -m saints_score run-all --config config.toml
"""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING

import click
import polars as pl

from saints_score.config import get_settings
from saints_score.io.run_log import RunLog
from saints_score.logging import logger, setup_logging

if TYPE_CHECKING:
    pass


# ── Shared options ───────────────────────────────────────────────────────

def _common_options(f):
    """Shared Click options for every pipeline command."""
    f = click.option(
        "--config", "config_path",
        type=click.Path(exists=True), default="config.toml",
        help="Path to config.toml.",
    )(f)
    f = click.option(
        "--dry-run", is_flag=True,
        help="Parse/compute but do not write files.",
    )(f)
    f = click.option(
        "--limit", type=int, default=None,
        help="Cap row/post counts for smoke testing.",
    )(f)
    return f


@click.group()
@click.version_option(package_name="saints-score")
def cli() -> None:
    """Saints Score — quantifying attacker canonization in online extremist communities."""


# ── Phase 1: Ingest ──────────────────────────────────────────────────────

@cli.command()
@_common_options
@click.option("--cases-only", is_flag=True, help="Only process the cases dataset.")
def ingest(config_path: str, dry_run: bool, limit: int | None, cases_only: bool) -> None:
    """Phase 1: Ingest /pol/ and validate cases."""
    cfg = get_settings(config_path)
    run = RunLog(phase="01_ingest", config=cfg.model_dump(mode="json"))
    setup_logging(log_file=cfg.runs / "01_ingest" / "stdout.log" if not dry_run else None)

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

    logger.info("=== Ingesting /pol/ corpus ===")
    from saints_score.ingest.pol import ingest_pol

    # Cache check: skip ingest if partitioned parquet already exists
    existing_parquets = list(cfg.pol_parquet.rglob("*.parquet")) if cfg.pol_parquet.exists() else []
    if existing_parquets and not dry_run:
        logger.info(
            "Found {} existing partition files in {}. Skipping re-ingest (delete to force).",
            len(existing_parquets), cfg.pol_parquet,
        )
        manifest = {"total_rows": "cached", "cached": True}
        run.metrics = {**cases_report, "pol_manifest": manifest}
    elif not cfg.pol_tar.exists():
        logger.error("/pol/ tar not found: {}. Skipping ingest.", cfg.pol_tar)
    else:
        if not dry_run:
            run.hash_input(cfg.pol_tar)
        manifest = ingest_pol(cfg, limit=limit, dry_run=dry_run)
        run.metrics = {**cases_report, "pol_manifest": manifest}
        logger.info("Ingest complete. Total rows: {}", manifest.get("total_rows", 0))

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
    logger.info("Phase 1 complete. Awaiting go/no-go for Phase 2.")


# ── Phase 2: Mentions ────────────────────────────────────────────────────

@cli.command()
@_common_options
@click.option("--round", "bootstrap_round", type=int, default=1, help="Bootstrap iteration (1-3).")
def mentions(
    config_path: str, dry_run: bool, limit: int | None, bootstrap_round: int,
) -> None:
    """Phase 2: Detect attacker mentions (multi-stage)."""
    cfg = get_settings(config_path)
    run = RunLog(phase="02_mentions", config=cfg.model_dump(mode="json"))
    setup_logging(log_file=cfg.runs / "02_mentions" / "stdout.log" if not dry_run else None)

    from saints_score.io.parquet import read_parquet, scan_partitioned, write_parquet

    cases_path = cfg.resolve(cfg.data_processed) / "cases.parquet"
    if not cases_path.exists():
        logger.error("Cases not found at {}. Run Phase 1 first.", cases_path)
        sys.exit(1)
    cases = read_parquet(cases_path)
    logger.info("Loaded {} cases", cases.height)

    pol_dir = cfg.pol_parquet
    if not pol_dir.exists():
        logger.error("/pol/ parquet not found: {}. Run Phase 1 first.", pol_dir)
        sys.exit(1)
    posts_lf = scan_partitioned(pol_dir)
    if limit:
        posts_lf = posts_lf.head(limit)

    # Stage 1: Seed aliases
    logger.info("=== Stage 1: Building seed alias inventory ===")
    from saints_score.mentions.aliases import build_seed_aliases, save_seed_aliases

    aliases = build_seed_aliases(cases)
    if not dry_run:
        save_seed_aliases(aliases, cfg)

    # Stage 2: Lexical retrieval
    logger.info("=== Stage 2: Lexical candidate retrieval ===")
    from saints_score.mentions.lexical import lexical_candidate_retrieval

    lex_candidates = lexical_candidate_retrieval(posts_lf, aliases, cfg)
    logger.info("Lexical candidates: {}", lex_candidates.height)

    # Stage 3: Semantic retrieval
    # Full-corpus embedding is infeasible at 284M rows.  Instead we embed
    # posts from threads that already have a lexical match (contextual
    # neighbours) plus a controlled random sample, capped to avoid OOM.
    logger.info("=== Stage 3: Semantic candidate retrieval ===")
    from saints_score.mentions.semantic import (
        build_attacker_probes,
        embed_texts,
        semantic_candidate_retrieval,
    )

    MAX_EMBED_POSTS = 2_000_000  # upper bound for GPU/RAM budget

    # Identify threads containing lexical matches
    lex_post_ids = lex_candidates["post_id"].unique()
    lex_thread_ids = (
        posts_lf.filter(pl.col("post_id").is_in(lex_post_ids))
        .select("thread_id")
        .unique()
        .collect()["thread_id"]
    )
    # Collect posts from those threads (contextual neighbours)
    thread_posts = (
        posts_lf.filter(pl.col("thread_id").is_in(lex_thread_ids))
        .select(["post_id", "body_clean"])
        .collect()
    )
    logger.info(
        "Thread-neighbour posts for embedding: {} (from {} threads)",
        thread_posts.height,
        len(lex_thread_ids),
    )
    if thread_posts.height > MAX_EMBED_POSTS:
        thread_posts = thread_posts.sample(n=MAX_EMBED_POSTS, seed=cfg.seed)
        logger.info("Capped to {} posts for embedding", MAX_EMBED_POSTS)

    posts_for_embed = thread_posts
    texts = posts_for_embed["body_clean"].to_list()
    post_ids = posts_for_embed["post_id"].to_list()

    if texts:
        post_embeddings = embed_texts(texts, cfg)
        probes = build_attacker_probes(cases)
        sem_candidates = semantic_candidate_retrieval(post_embeddings, post_ids, probes, cfg)
        logger.info("Semantic candidates (raw): {}", sem_candidates.height)

        # Keep only the top-50 per attacker (by similarity) to cap noise.
        # The cross-encoder handles the ~7 950 resulting pairs in seconds.
        MAX_SEM_PER_ATTACKER = 50
        sem_candidates = (
            sem_candidates.sort("similarity", descending=True)
            .group_by("attacker_id")
            .head(MAX_SEM_PER_ATTACKER)
        )
        logger.info(
            "Semantic candidates after top-{}/attacker: {}",
            MAX_SEM_PER_ATTACKER,
            sem_candidates.height,
        )

        # Preserve alias_matched (null for semantic) for downstream provenance
        all_candidates = pl.concat(
            [
                lex_candidates.select(["post_id", "attacker_id", "match_type", "alias_matched"]),
                sem_candidates.select(["post_id", "attacker_id", "match_type"]).with_columns(
                    pl.lit(None, dtype=pl.Utf8).alias("alias_matched")
                ),
            ]
        ).unique(subset=["post_id", "attacker_id"])
    else:
        all_candidates = lex_candidates

    # Stage 4: Cross-encoder adjudication
    logger.info("=== Stage 4: Cross-encoder adjudication ===")
    # Release embedding model VRAM before loading the cross-encoder
    from saints_score.mentions.semantic import release_embedding_resources
    release_embedding_resources()

    # Only collect posts that are actual candidates (avoid full-corpus collect)
    candidate_pids = all_candidates["post_id"].unique()
    posts_df = posts_lf.filter(pl.col("post_id").is_in(candidate_pids)).collect()
    from saints_score.mentions.adjudicate import adjudicate_candidates, filter_mentions

    adjudicated = adjudicate_candidates(
        all_candidates, posts_df, cases, cfg, max_candidates=limit,
    )
    mention_df = filter_mentions(adjudicated, cfg)

    # Output
    if not dry_run:
        mentions_path = cfg.resolve(cfg.data_processed) / "mentions.parquet"
        write_parquet(mention_df, mentions_path)
        run.hash_output(mentions_path)
        write_parquet(aliases, cfg.resolve(cfg.data_processed) / "aliases_final.parquet")

    run.metrics = {
        "n_mentions": mention_df.height,
        "n_attackers_with_mentions": mention_df["attacker_id"].n_unique(),
        "n_lexical_candidates": lex_candidates.height,
        "bootstrap_round": bootstrap_round,
    }

    if not dry_run:
        summary_dir = run.save(cfg.runs)
        (summary_dir / "SUMMARY.md").write_text(
            f"# Phase 2 — Mention Detection Summary\n\n"
            f"- Seed aliases: {aliases.height}\n"
            f"- Lexical candidates: {lex_candidates.height}\n"
            f"- Final mentions: {mention_df.height}\n"
            f"- Attackers with mentions: {mention_df['attacker_id'].n_unique()}\n"
            f"- Bootstrap round: {bootstrap_round}\n",
            encoding="utf-8",
        )
    logger.info("Phase 2 complete. Awaiting go/no-go for Phase 3.")


# ── Phase 3: Affect ──────────────────────────────────────────────────────

@cli.command()
@_common_options
def affect(config_path: str, dry_run: bool, limit: int | None) -> None:
    """Phase 3: Score affect (sentiment + emotion + toxicity)."""
    cfg = get_settings(config_path)
    run = RunLog(phase="03_affect", config=cfg.model_dump(mode="json"))
    setup_logging(log_file=cfg.runs / "03_affect" / "stdout.log" if not dry_run else None)

    from saints_score.io.parquet import read_parquet, scan_partitioned

    mentions_path = cfg.resolve(cfg.data_processed) / "mentions.parquet"
    if not mentions_path.exists():
        logger.error("Mentions not found. Run Phase 2 first.")
        sys.exit(1)
    mention_df = read_parquet(mentions_path)

    # Sample at most MAX_AFFECT_PER_ATTACKER posts per attacker before the
    # expensive cross-corpus collect. 18M posts × 3 models = days; 1000/attacker
    # is statistically sufficient for affect-distribution estimation.
    MAX_AFFECT_PER_ATTACKER = 1_000
    rng = cfg.seed
    sampled = (
        mention_df
        .with_columns(pl.int_range(pl.len(), dtype=pl.UInt32).shuffle(seed=rng).alias("_rng"))
        .sort("_rng")
        .group_by("attacker_id")
        .head(MAX_AFFECT_PER_ATTACKER)
        .drop("_rng")
    )
    logger.info(
        "Affect: sampled {}/{} mentions ({} per attacker cap)",
        sampled.height, mention_df.height, MAX_AFFECT_PER_ATTACKER,
    )
    mention_df = sampled

    posts_lf = scan_partitioned(cfg.pol_parquet)
    mention_pids = mention_df.select("post_id").unique()
    logger.info("Collecting {} unique post texts from corpus", mention_pids.height)
    posts = posts_lf.filter(pl.col("post_id").is_in(mention_pids["post_id"])).collect()
    logger.info("Collected {} posts", posts.height)

    if limit:
        posts = posts.head(limit)
        mention_df = mention_df.filter(pl.col("post_id").is_in(posts["post_id"]))

    from saints_score.affect.classify import run_affect_pipeline

    affect_df = run_affect_pipeline(mention_df, posts, cfg)

    run.metrics = {"n_posts_scored": affect_df.height, "columns": affect_df.columns}
    if not dry_run:
        affect_path = cfg.resolve(cfg.data_processed) / "affect_scores.parquet"
        # run_affect_pipeline already writes the file; hash it for provenance
        run.hash_output(affect_path)
        summary_dir = run.save(cfg.runs)
        (summary_dir / "SUMMARY.md").write_text(
            f"# Phase 3 — Affect Scoring Summary\n\n"
            f"- Posts scored: {affect_df.height}\n"
            f"- Columns: {len(affect_df.columns)}\n",
            encoding="utf-8",
        )
    logger.info("Phase 3 complete. Awaiting domain-validity review.")


# ── Phase 4: Temporal ────────────────────────────────────────────────────

@cli.command()
@_common_options
def temporal(config_path: str, dry_run: bool, limit: int | None) -> None:
    """Phase 4: Compute temporal metrics (intensity, longevity)."""
    cfg = get_settings(config_path)
    run = RunLog(phase="04_temporal", config=cfg.model_dump(mode="json"))
    setup_logging(log_file=cfg.runs / "04_temporal" / "stdout.log" if not dry_run else None)

    from saints_score.io.parquet import read_parquet, scan_partitioned

    mention_df = read_parquet(cfg.resolve(cfg.data_processed) / "mentions.parquet")
    cases = read_parquet(cfg.resolve(cfg.data_processed) / "cases.parquet")

    if limit:
        mention_df = mention_df.head(limit)

    # Only select the two columns temporal metrics need (post_id + timestamp).
    # Fetching all columns for 18M posts would require 60+ GB RAM.
    mention_pids_t = mention_df["post_id"].unique()
    logger.info("Collecting timestamps for {} unique posts", mention_pids_t.len())
    posts = (
        scan_partitioned(cfg.pol_parquet)
        .filter(pl.col("post_id").is_in(mention_pids_t))
        .select(["post_id", "timestamp_utc"])
        .collect()
    )
    logger.info("Collected {} post timestamps", posts.height)

    from saints_score.temporal.metrics import compute_daily_counts, compute_temporal_metrics

    temporal_df = compute_temporal_metrics(mention_df, posts, cases, cfg)

    if not dry_run:
        from saints_score.viz.plots import plot_decay_curve

        daily = compute_daily_counts(mention_df, posts)
        fig_dir = cfg.resolve(cfg.out_dir) / "figures" / "decay_per_attacker"
        for row in temporal_df.iter_rows(named=True):
            case_row = cases.filter(pl.col("case_id") == row["attacker_id"])
            if case_row.height > 0:
                plot_decay_curve(
                    daily, row["attacker_id"], case_row["event_date"][0],
                    row.get("alpha"), row.get("C"), fig_dir,
                )

    run.metrics = {
        "n_attackers": temporal_df.height,
        "fit_success_rate": temporal_df.filter(pl.col("fit_success")).height
        / max(temporal_df.height, 1),
    }
    if not dry_run:
        run.hash_output(cfg.resolve(cfg.data_processed) / "temporal_metrics.parquet")
        summary_dir = run.save(cfg.runs)
        (summary_dir / "SUMMARY.md").write_text(
            f"# Phase 4 — Temporal Metrics Summary\n\n"
            f"- Attackers: {temporal_df.height}\n"
            f"- Decay fit success rate: {run.metrics['fit_success_rate']:.1%}\n",
            encoding="utf-8",
        )
    logger.info("Phase 4 complete. Inspect decay fits per attacker.")


# ── Phase 5: Semantic ────────────────────────────────────────────────────

@cli.command()
@_common_options
def semantic(config_path: str, dry_run: bool, limit: int | None) -> None:
    """Phase 5: Compute semantic convergence metrics."""
    cfg = get_settings(config_path)
    run = RunLog(phase="05_semantic", config=cfg.model_dump(mode="json"))
    setup_logging(log_file=cfg.runs / "05_semantic" / "stdout.log" if not dry_run else None)

    from saints_score.io.parquet import read_parquet, scan_partitioned

    mention_df = read_parquet(cfg.resolve(cfg.data_processed) / "mentions.parquet")
    cases = read_parquet(cfg.resolve(cfg.data_processed) / "cases.parquet")

    if limit:
        mention_df = mention_df.head(limit)

    # Cap per-attacker before expensive collection (embedding needs text; 500/attacker
    # gives adequate per-attacker sample for convergence estimation).
    MAX_SEM_PER_ATTACKER = 500
    mention_df = (
        mention_df
        .with_columns(pl.int_range(pl.len(), dtype=pl.UInt32).shuffle(seed=cfg.seed).alias("_rng"))
        .sort("_rng")
        .group_by("attacker_id")
        .head(MAX_SEM_PER_ATTACKER)
        .drop("_rng")
    )
    mention_pids_s = mention_df["post_id"].unique()
    logger.info("Semantic: collecting {} posts ({} per attacker cap)", mention_pids_s.len(), MAX_SEM_PER_ATTACKER)
    posts = scan_partitioned(cfg.pol_parquet).filter(
        pl.col("post_id").is_in(mention_pids_s)
    ).collect()
    logger.info("Collected {} posts for semantic scoring", posts.height)

    from saints_score.semantic.convergence import compute_semantic_metrics

    semantic_df = compute_semantic_metrics(mention_df, posts, cases, cfg)

    run.metrics = {"n_attackers": semantic_df.height}
    if not dry_run:
        run.hash_output(cfg.resolve(cfg.data_processed) / "semantic_metrics.parquet")
        summary_dir = run.save(cfg.runs)
        (summary_dir / "SUMMARY.md").write_text(
            f"# Phase 5 — Semantic Convergence Summary\n\n"
            f"- Attackers scored: {semantic_df.height}\n",
            encoding="utf-8",
        )
    logger.info("Phase 5 complete. Inspect similarity distributions.")


# ── Phase 6: Score ───────────────────────────────────────────────────────

@cli.command()
@_common_options
@click.option("--skip-bayes", is_flag=True, help="Skip Bayesian model (fast mode).")
def score(config_path: str, dry_run: bool, limit: int | None, skip_bayes: bool) -> None:
    """Phase 6: Compute composite Saints Score (naive + Bayesian)."""
    cfg = get_settings(config_path)
    run = RunLog(phase="06_scoring", config=cfg.model_dump(mode="json"))
    setup_logging(log_file=cfg.runs / "06_scoring" / "stdout.log" if not dry_run else None)

    from saints_score.io.parquet import read_parquet

    processed = cfg.resolve(cfg.data_processed)
    affect_df = read_parquet(processed / "affect_scores.parquet")
    temporal_df = read_parquet(processed / "temporal_metrics.parquet")
    semantic_df = read_parquet(processed / "semantic_metrics.parquet")
    mention_df = read_parquet(processed / "mentions.parquet")

    from saints_score.scoring.composite import compute_naive_score

    naive = compute_naive_score(affect_df, temporal_df, semantic_df, mention_df, cfg)

    bayes = None
    if not skip_bayes:
        from saints_score.scoring.composite import compute_bayesian_score

        bayes = compute_bayesian_score(affect_df, temporal_df, semantic_df, mention_df, cfg)

    if bayes is not None and not dry_run:
        from saints_score.viz.plots import plot_saints_comparison

        plot_saints_comparison(naive, bayes, cfg.resolve(cfg.out_dir) / "figures")

    run.metrics = {"n_naive": naive.height, "n_bayes": bayes.height if bayes is not None else 0}
    if not dry_run:
        summary_dir = run.save(cfg.runs)
        (summary_dir / "SUMMARY.md").write_text(
            f"# Phase 6 — Saints Score Assembly Summary\n\n"
            f"- Naive scores: {naive.height}\n"
            f"- Bayesian scores: {bayes.height if bayes is not None else 'skipped'}\n",
            encoding="utf-8",
        )
    logger.info("Phase 6 complete. Check face validity before Phase 7.")


# ── Phase 7: Regression ──────────────────────────────────────────────────

@cli.command()
@_common_options
def regression(config_path: str, dry_run: bool, limit: int | None) -> None:
    """Phase 7: Fit attack-characteristic regression."""
    cfg = get_settings(config_path)
    run = RunLog(phase="07_regression", config=cfg.model_dump(mode="json"))
    setup_logging(log_file=cfg.runs / "07_regression" / "stdout.log" if not dry_run else None)

    scores_path = cfg.resolve(cfg.out_dir) / "scores" / "saints_bayes.csv"
    if not scores_path.exists():
        logger.error("Bayesian scores not found. Run Phase 6 first.")
        sys.exit(1)

    saints = pl.read_csv(scores_path)
    from saints_score.io.parquet import read_parquet

    cases = read_parquet(cfg.resolve(cfg.data_processed) / "cases.parquet")

    from saints_score.models.regression import fit_regression, prepare_regression_data

    data = prepare_regression_data(saints, cases)
    if dry_run:
        logger.info("Dry run — skipping model fitting ({} obs).", data.height)
        return

    _trace, coef_df = fit_regression(data, cfg)

    from saints_score.viz.plots import plot_regression_forest

    plot_regression_forest(coef_df, cfg.resolve(cfg.out_dir) / "figures")

    run.metrics = {"n_observations": data.height, "n_predictors": coef_df.height}
    summary_dir = run.save(cfg.runs)
    (summary_dir / "SUMMARY.md").write_text(
        f"# Phase 7 — Regression Summary\n\n"
        f"- Observations: {data.height}\n"
        f"- Predictors: {coef_df.height}\n",
        encoding="utf-8",
    )
    logger.info("Phase 7 complete. Review PPC + LOO diagnostics.")


# ── Linguistic evolution tracking ────────────────────────────────────────

@cli.command(name="drift")
@_common_options
def linguistic_drift(config_path: str, dry_run: bool, limit: int | None) -> None:
    """Track embedding-space drift of attacker discourse over time (ConTEXT-inspired)."""
    cfg = get_settings(config_path)
    run = RunLog(phase="08_drift", config=cfg.model_dump(mode="json"))
    setup_logging(log_file=cfg.runs / "08_drift" / "stdout.log" if not dry_run else None)

    from saints_score.io.parquet import read_parquet, scan_partitioned

    mentions_path = cfg.resolve(cfg.data_processed) / "mentions.parquet"
    if not mentions_path.exists():
        logger.error("Mentions not found. Run Phase 2 first.")
        sys.exit(1)

    mention_df = read_parquet(mentions_path)
    cases = read_parquet(cfg.resolve(cfg.data_processed) / "cases.parquet")

    if limit:
        mention_df = mention_df.head(limit)

    # Cap per-attacker before collection (drift analysis uses embeddings; 500/attacker
    # preserves temporal ordering needed for window-based drift computation).
    MAX_DRIFT_PER_ATTACKER = 500
    mention_df = (
        mention_df
        .with_columns(pl.int_range(pl.len(), dtype=pl.UInt32).shuffle(seed=cfg.seed).alias("_rng"))
        .sort("_rng")
        .group_by("attacker_id")
        .head(MAX_DRIFT_PER_ATTACKER)
        .drop("_rng")
    )
    mention_pids_d = mention_df["post_id"].unique()
    logger.info("Drift: collecting {} posts ({} per attacker cap)", mention_pids_d.len(), MAX_DRIFT_PER_ATTACKER)
    posts = scan_partitioned(cfg.pol_parquet).filter(
        pl.col("post_id").is_in(mention_pids_d)
    ).collect()
    logger.info("Collected {} posts for drift analysis", posts.height)

    from saints_score.semantic.drift import compute_drift_metrics

    drift_df = compute_drift_metrics(mention_df, posts, cases, cfg)

    run.metrics = {"n_attackers_tracked": drift_df["attacker_id"].n_unique()}

    if not dry_run:
        from saints_score.io.parquet import write_parquet

        out_path = cfg.resolve(cfg.data_processed) / "drift_metrics.parquet"
        write_parquet(drift_df, out_path)
        run.hash_output(out_path)
        summary_dir = run.save(cfg.runs)
        (summary_dir / "SUMMARY.md").write_text(
            f"# Phase 8 — Linguistic Drift Summary\n\n"
            f"- Attackers tracked: {drift_df['attacker_id'].n_unique()}\n"
            f"- Total time windows: {drift_df.height}\n",
            encoding="utf-8",
        )
    logger.info("Phase 8 (drift) complete.")


# ── Run all phases ───────────────────────────────────────────────────────

@cli.command(name="run-all")
@_common_options
@click.option("--skip-bayes", is_flag=True)
def run_all(config_path: str, dry_run: bool, limit: int | None, skip_bayes: bool) -> None:
    """Run all pipeline phases sequentially."""
    ctx = click.get_current_context()
    phases = [
        ("ingest", {"config_path": config_path, "dry_run": dry_run, "limit": limit, "cases_only": False}),
        ("mentions", {"config_path": config_path, "dry_run": dry_run, "limit": limit, "bootstrap_round": 1}),
        ("affect", {"config_path": config_path, "dry_run": dry_run, "limit": limit}),
        ("temporal", {"config_path": config_path, "dry_run": dry_run, "limit": limit}),
        ("semantic", {"config_path": config_path, "dry_run": dry_run, "limit": limit}),
        ("score", {"config_path": config_path, "dry_run": dry_run, "limit": limit, "skip_bayes": skip_bayes}),
        ("regression", {"config_path": config_path, "dry_run": dry_run, "limit": limit}),
        ("drift", {"config_path": config_path, "dry_run": dry_run, "limit": limit}),
    ]
    for name, kwargs in phases:
        logger.info("=" * 60)
        logger.info("Running phase: {}", name)
        logger.info("=" * 60)
        ctx.invoke(cli.commands[name], **kwargs)


def main() -> None:
    """Entry point for ``python -m saints_score``."""
    cli()
