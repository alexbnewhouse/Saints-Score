"""Alias bootstrapping (§6.2 stage 5).

From positive adjudications, extract high-TF-IDF tokens that co-occur
disproportionately with an attacker, surfacing candidate new aliases.
"""

from __future__ import annotations

import math
import re
from collections import Counter

import polars as pl

from saints_score.logging import logger


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\b\w{3,}\b", text.lower())


def extract_candidate_aliases(
    mentions: pl.DataFrame,
    posts: pl.DataFrame,
    baseline_posts: pl.DataFrame,
    *,
    top_n: int = 30,
) -> pl.DataFrame:
    """Extract high-TF-IDF tokens from positive mentions vs random baseline.

    Returns a DataFrame with columns:
        ``attacker_id``, ``candidate_alias``, ``tfidf_score``, ``mention_count``
    """
    # Build baseline term frequencies
    baseline_texts = baseline_posts.select("body_clean").to_series().to_list()
    baseline_tf: Counter[str] = Counter()
    n_baseline = 0
    for text in baseline_texts:
        if text:
            tokens = _tokenize(text)
            baseline_tf.update(set(tokens))
            n_baseline += 1

    results: list[dict] = []

    for attacker_id in mentions["attacker_id"].unique().to_list():
        atk_post_ids = (
            mentions.filter(pl.col("attacker_id") == attacker_id)
            .select("post_id")
            .to_series()
            .to_list()
        )
        atk_posts = posts.filter(pl.col("post_id").is_in(atk_post_ids))
        atk_texts = atk_posts.select("body_clean").to_series().to_list()

        # Term frequency in attacker mention set
        atk_tf: Counter[str] = Counter()
        n_atk = 0
        for text in atk_texts:
            if text:
                tokens = _tokenize(text)
                atk_tf.update(set(tokens))
                n_atk += 1

        if n_atk == 0:
            continue

        # TF-IDF-like score: TF in mention set × log(N_baseline / (1 + DF_baseline))
        scored: list[tuple[str, float, int]] = []
        for token, count in atk_tf.items():
            if count < 3:  # minimum occurrence threshold
                continue
            tf = count / n_atk
            df_baseline = baseline_tf.get(token, 0)
            idf = math.log((n_baseline + 1) / (1 + df_baseline))
            score = tf * idf
            scored.append((token, score, count))

        scored.sort(key=lambda x: x[1], reverse=True)
        for token, score, count in scored[:top_n]:
            results.append({
                "attacker_id": attacker_id,
                "candidate_alias": token,
                "tfidf_score": round(score, 4),
                "mention_count": count,
            })

    if not results:
        return pl.DataFrame(
            schema={
                "attacker_id": pl.Utf8,
                "candidate_alias": pl.Utf8,
                "tfidf_score": pl.Float64,
                "mention_count": pl.Int64,
            }
        )

    df = pl.DataFrame(results)
    logger.info("Extracted {} candidate aliases for {} attackers",
                df.height, df["attacker_id"].n_unique())
    return df
