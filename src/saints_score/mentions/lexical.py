"""Candidate retrieval — lexical and fuzzy matching for mention detection.

Stage 2 of §6.2: exact substring, rapidfuzz, and phonetic matching.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import polars as pl
from rapidfuzz import fuzz

from saints_score.logging import logger

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

    # Build regex pattern for exact matching (all aliases)
    all_aliases = []
    alias_to_attacker: dict[str, str] = {}
    for aid, alias_list in alias_map.items():
        for alias in alias_list:
            if len(alias) >= cfg.min_alias_token_len:
                all_aliases.append(re.escape(alias.lower()))
                alias_to_attacker[alias.lower()] = aid

    if not all_aliases:
        logger.warning("No aliases long enough for matching (min len: {})", cfg.min_alias_token_len)
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
        len(all_aliases), len(alias_map), len(pattern),
    )

    # Collect the posts we need (body_clean already lowercased)
    posts_df = posts.select(["post_id", "body_clean"]).collect()

    # Exact matches
    exact_matches = posts_df.filter(
        pl.col("body_clean").str.contains(f"(?i)(?:{pattern})")
    )

    results: list[dict] = []
    for row in exact_matches.iter_rows(named=True):
        text = row["body_clean"].lower()
        for alias_lower, aid in alias_to_attacker.items():
            if alias_lower in text:
                results.append({
                    "post_id": row["post_id"],
                    "attacker_id": aid,
                    "alias_matched": alias_lower,
                    "match_type": "exact_substring",
                    "score": 1.0,
                })

    # Phase 2: Fuzzy matching on posts NOT already matched
    matched_ids = {r["post_id"] for r in results}
    # Sample unmatched posts for fuzzy pass (too expensive on full corpus)
    unmatched = posts_df.filter(~pl.col("post_id").is_in(list(matched_ids)))

    # For fuzzy matching, check tokens against alias tokens
    long_aliases = [
        (alias, aid) for alias, aid in alias_to_attacker.items()
        if len(alias.split()) <= 3  # only fuzzy-match short aliases
    ]

    fuzzy_results: list[dict] = []
    # Process in batches to manage memory
    sample_size = min(unmatched.height, 500_000)
    if sample_size > 0 and long_aliases:
        sample = unmatched.sample(n=sample_size, seed=20260414) if unmatched.height > sample_size else unmatched
        logger.info("Fuzzy matching {} posts against {} aliases", sample.height, len(long_aliases))

        for row in sample.iter_rows(named=True):
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
                            fuzzy_results.append({
                                "post_id": row["post_id"],
                                "attacker_id": aid,
                                "alias_matched": alias,
                                "match_type": "fuzzy",
                                "score": ratio / 100.0,
                            })
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
    logger.info("Lexical retrieval: {} candidates ({} exact, {} fuzzy)",
                df.height, len(results), len(fuzzy_results))
    return df
