"""Semantic convergence metrics (§6.5).

Pairwise cosine similarity, topic concentration via HDBSCAN, and unigram entropy.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import TYPE_CHECKING, Any

import numpy as np
import polars as pl

from saints_score.io.parquet import write_parquet
from saints_score.logging import logger
from saints_score.mentions.semantic import embed_texts

if TYPE_CHECKING:
    from saints_score.config import Settings


def compute_similarity(
    embeddings: np.ndarray,
    *,
    max_sample: int = 10_000,
    seed: int = 20260414,
) -> dict[str, float]:
    """Compute pairwise cosine similarity statistics.

    Parameters
    ----------
    embeddings:
        (N, D) normalised embedding matrix.
    max_sample:
        Subsample to this many posts for pairwise computation.

    Returns
    -------
    Dict with ``median``, ``iqr``, ``mean``, ``std``, ``n``.
    """
    n = embeddings.shape[0]
    if n <= 1:
        return {"median": 0.0, "iqr": 0.0, "mean": 0.0, "std": 0.0, "n": n}

    if n > max_sample:
        rng = np.random.default_rng(seed)
        idx = rng.choice(n, size=max_sample, replace=False)
        embeddings = embeddings[idx]
        n = max_sample

    # Pairwise cosine sim (embeddings are normalised)
    sim_matrix = embeddings @ embeddings.T
    # Extract upper triangle (exclude diagonal)
    triu_idx = np.triu_indices(n, k=1)
    sims = sim_matrix[triu_idx]

    return {
        "median": float(np.median(sims)),
        "iqr": float(np.percentile(sims, 75) - np.percentile(sims, 25)),
        "mean": float(np.mean(sims)),
        "std": float(np.std(sims)),
        "n": n,
    }


def compute_topic_concentration(
    embeddings: np.ndarray,
    *,
    min_cluster_size: int = 15,
) -> dict[str, Any]:
    """Cluster embeddings with HDBSCAN and report top-3 cluster concentration.

    Returns dict with ``n_clusters``, ``top3_proportion``, ``noise_proportion``.
    """
    try:
        from sklearn.cluster import HDBSCAN
    except ImportError:
        logger.warning("HDBSCAN not available; skipping topic concentration")
        return {"n_clusters": None, "top3_proportion": None, "noise_proportion": None}

    if embeddings.shape[0] < min_cluster_size * 2:
        return {"n_clusters": 0, "top3_proportion": 0.0, "noise_proportion": 1.0}

    clusterer = HDBSCAN(min_cluster_size=min_cluster_size)
    labels = clusterer.fit_predict(embeddings)

    unique, counts = np.unique(labels, return_counts=True)
    cluster_counts = {int(lbl): int(c) for lbl, c in zip(unique, counts, strict=False)}
    noise = cluster_counts.pop(-1, 0)
    total = len(labels)

    n_clusters = len(cluster_counts)
    sorted_counts = sorted(cluster_counts.values(), reverse=True)
    top3 = sum(sorted_counts[:3])
    non_noise = total - noise

    return {
        "n_clusters": n_clusters,
        "top3_proportion": top3 / non_noise if non_noise > 0 else 0.0,
        "noise_proportion": noise / total if total > 0 else 0.0,
    }


def compute_unigram_entropy(texts: list[str]) -> float:
    """Compute unigram entropy over content tokens as a non-embedding baseline."""
    counter: Counter[str] = Counter()
    for text in texts:
        tokens = re.findall(r"\b\w{3,}\b", text.lower())
        counter.update(tokens)

    total = sum(counter.values())
    if total == 0:
        return 0.0

    entropy = 0.0
    for count in counter.values():
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)
    return entropy


def compute_semantic_metrics(
    mentions: pl.DataFrame,
    posts: pl.DataFrame,
    cases: pl.DataFrame,
    cfg: Settings,
) -> pl.DataFrame:
    """Full Phase 5: compute semantic convergence metrics per attacker."""
    results: list[dict[str, Any]] = []

    for attacker_id in mentions["attacker_id"].unique().to_list():
        atk_post_ids = (
            mentions.filter(pl.col("attacker_id") == attacker_id)
            .select("post_id")
            .to_series()
            .to_list()
        )
        atk_posts = posts.filter(pl.col("post_id").is_in(atk_post_ids))

        if atk_posts.height < 5:
            logger.warning("Attacker {} has only {} posts, skipping", attacker_id, atk_posts.height)
            continue

        texts = atk_posts.select("body_clean").to_series().to_list()

        # Embed
        embeddings = embed_texts(texts, cfg, show_progress=False)

        # Similarity
        sim_stats = compute_similarity(embeddings, seed=cfg.seed)

        # Topic concentration
        topic_stats = compute_topic_concentration(embeddings)

        # Unigram entropy
        entropy = compute_unigram_entropy(texts)

        results.append({
            "attacker_id": attacker_id,
            "similarity_median": sim_stats["median"],
            "similarity_iqr": sim_stats["iqr"],
            "similarity_mean": sim_stats["mean"],
            "similarity_std": sim_stats["std"],
            "similarity_n": sim_stats["n"],
            "n_clusters": topic_stats["n_clusters"],
            "top3_cluster_proportion": topic_stats["top3_proportion"],
            "noise_proportion": topic_stats["noise_proportion"],
            "unigram_entropy": entropy,
        })

    df = pl.DataFrame(results)
    out_path = cfg.resolve(cfg.data_processed) / "semantic_metrics.parquet"
    write_parquet(df, out_path)
    logger.info("Semantic metrics: {} attackers", df.height)
    return df
