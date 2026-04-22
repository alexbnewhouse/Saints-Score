"""Candidate retrieval — lexical and fuzzy matching for mention detection.

Stage 2 of §6.2: exact substring, rapidfuzz, and phonetic matching.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import polars as pl
from rapidfuzz import fuzz

from saints_score.logging import logger
from saints_score.mentions.adversarial import (
    consonant_skeleton,
    generate_adversarial_variants,
    normalize_adversarial,
)

if TYPE_CHECKING:
    from saints_score.config import Settings


def _tokenize(text: str) -> list[str]:
    """Simple whitespace tokenizer, lowercased."""
    return re.findall(r"\b\w+\b", text.lower())


def lexical_candidate_retrieval(
    posts: pl.LazyFrame,
    aliases: pl.DataFrame,
    cfg: Settings,
) -> pl.DataFrame:
    """Retrieve mention candidates via lexical matching.

    For each alias:
    1. Exact case-insensitive substring match
    2. Fuzzy token ratio ≥ ``cfg.fuzzy_threshold`` on tokens ≥ 4 chars

    Returns a DataFrame with columns:
        ``post_id``, ``attacker_id``, ``alias_matched``, ``match_type``, ``score``
    """
    # Collect aliases grouped by attacker
    alias_map: dict[str, list[str]] = {}
    for row in aliases.iter_rows(named=True):
        aid = row["attacker_id"]
        alias_map.setdefault(aid, []).append(row["alias"])

    # Build regex pattern for exact matching (all aliases + adversarial variants)
    all_aliases = []
    alias_to_attacker: dict[str, str] = {}
    adversarial_variants: dict[str, str] = {}  # variant → attacker_id
    for aid, alias_list in alias_map.items():
        for alias in alias_list:
            if len(alias) >= cfg.min_alias_token_len:
                all_aliases.append(re.escape(alias.lower()))
                alias_to_attacker[alias.lower()] = aid
                # Generate adversarial variants
                for variant in generate_adversarial_variants(alias):
                    if len(variant) >= cfg.min_alias_token_len and variant not in alias_to_attacker:
                        adversarial_variants[variant] = aid

    if not all_aliases:
        logger.warning(
            "No aliases long enough for matching (min len: {})", cfg.min_alias_token_len
        )
        return pl.DataFrame(
            schema={
                "post_id": pl.Int64,
                "attacker_id": pl.Utf8,
                "alias_matched": pl.Utf8,
                "match_type": pl.Utf8,
                "score": pl.Float64,
            }
        )

    # Phase 1: Exact substring via Polars regex (fast, vectorised)
    pattern = "|".join(all_aliases)
    logger.info(
        "Lexical retrieval: {} aliases across {} attackers, pattern len {}",
        len(all_aliases),
        len(alias_map),
        len(pattern),
    )

    # Push exact match filter into the lazy frame before collecting
    exact_matches = (
        posts.select(["post_id", "body_clean"])
        .filter(pl.col("body_clean").str.contains(f"(?i)(?:{pattern})"))
        .collect()
    )

    results: list[dict] = []
    for row in exact_matches.iter_rows(named=True):
        text = row["body_clean"].lower()
        for alias_lower, aid in alias_to_attacker.items():
            if alias_lower in text:
                results.append(
                    {
                        "post_id": row["post_id"],
                        "attacker_id": aid,
                        "alias_matched": alias_lower,
                        "match_type": "exact_substring",
                        "score": 1.0,
                    }
                )

    # --- Streaming-friendly sampling for adversarial / fuzzy passes ---
    # Instead of collecting the entire corpus (~284M rows), sample ~500K
    # posts via modular arithmetic on post_id pushed into the LazyFrame.
    _SAMPLE_TARGET = 500_000
    total_posts = posts.select(pl.len()).collect().item()
    sample_mod = max(1, total_posts // _SAMPLE_TARGET)
    logger.info(
        "Corpus has {} posts; using mod-{} sampling for adversarial/fuzzy passes",
        total_posts, sample_mod,
    )

    # Phase 2: Adversarial-normalised matching
    if adversarial_variants:
        logger.info("Adversarial matching: {} variants", len(adversarial_variants))
        adv_sample = (
            posts.filter(pl.col("post_id") % sample_mod < 1)
            .select(["post_id", "body_clean"])
            .collect()
        )
        logger.info("Adversarial pass: sampled {} posts", adv_sample.height)
        for row in adv_sample.iter_rows(named=True):
            normed = normalize_adversarial(row["body_clean"])
            for variant, aid in adversarial_variants.items():
                if variant in normed:
                    results.append({
                        "post_id": row["post_id"],
                        "attacker_id": aid,
                        "alias_matched": variant,
                        "match_type": "adversarial_norm",
                        "score": 0.9,
                    })
            # Consonant skeleton matching
            for token in normed.split():
                if len(token) < cfg.min_alias_token_len:
                    continue
                skel = consonant_skeleton(token)
                for alias_lower, aid in alias_to_attacker.items():
                    alias_skel = consonant_skeleton(alias_lower)
                    if len(alias_skel) >= 3 and skel == alias_skel and token != alias_lower:
                        results.append({
                            "post_id": row["post_id"],
                            "attacker_id": aid,
                            "alias_matched": token,
                            "match_type": "phonetic_skeleton",
                            "score": 0.8,
                        })

    # Phase 3: Fuzzy matching on sampled posts (NOT full corpus)
    # For fuzzy matching, check tokens against alias tokens
    long_aliases = [
        (alias, aid)
        for alias, aid in alias_to_attacker.items()
        if len(alias.split()) <= 3  # only fuzzy-match short aliases
    ]

    fuzzy_results: list[dict] = []
    if long_aliases:
        # Use a different mod offset to get a mostly-disjoint sample
        fuzzy_sample = (
            posts.filter(pl.col("post_id") % sample_mod < 1)
            .select(["post_id", "body_clean"])
            .collect()
        )
        sample_size = fuzzy_sample.height
        logger.info("Fuzzy matching {} posts against {} aliases", sample_size, len(long_aliases))

        for row in fuzzy_sample.iter_rows(named=True):
            tokens = _tokenize(row["body_clean"])
            long_tokens = [t for t in tokens if len(t) >= cfg.min_alias_token_len]
            if not long_tokens:
                continue

            for alias, aid in long_aliases:
                alias_tokens = alias.split()
                for token in long_tokens:
                    for atk in alias_tokens:
                        if len(atk) < cfg.min_alias_token_len:
                            continue
                        ratio = fuzz.ratio(token, atk)
                        if ratio >= cfg.fuzzy_threshold:
                            fuzzy_results.append(
                                {
                                    "post_id": row["post_id"],
                                    "attacker_id": aid,
                                    "alias_matched": alias,
                                    "match_type": "fuzzy",
                                    "score": ratio / 100.0,
                                }
                            )
                            break
                    else:
                        continue
                    break

    all_results = results + fuzzy_results
    if not all_results:
        return pl.DataFrame(
            schema={
                "post_id": pl.Int64,
                "attacker_id": pl.Utf8,
                "alias_matched": pl.Utf8,
                "match_type": pl.Utf8,
                "score": pl.Float64,
            }
        )

    df = pl.DataFrame(all_results)
    df = df.unique(subset=["post_id", "attacker_id"])
    logger.info(
        "Lexical retrieval: {} candidates ({} exact, {} fuzzy)",
        df.height,
        len(results),
        len(fuzzy_results),
    )
    return df
