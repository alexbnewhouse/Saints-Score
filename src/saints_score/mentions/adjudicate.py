"""GPU cross-encoder adjudication for mention detection (§6.2 stage 4).

Replaces the previous Ollama LLM adjudicator with a sentence-transformers
CrossEncoder running entirely on GPU.  For ~19.87 M lexical candidates this
reduces wall-clock time from days (LLM, CPU-bound) to minutes (GPU batch).

Design — tiered confidence strategy
------------------------------------
``exact_substring`` matches  → accepted unconditionally (confidence = 1.0).
                                These are verified alias hits; cross-encoder
                                scoring would only add noise.
All other match types         → cross-encoder scores each (query, passage)
(fuzzy, adversarial_norm,       pair.  confidence = sigmoid(raw logit).
 phonetic_skeleton, semantic)   Accepted when confidence ≥
                                ``mention_confidence_threshold``.

Cross-encoder model: ``cross-encoder/ms-marco-MiniLM-L-6-v2``
  * 22 MB, trained on MS MARCO passage ranking
  * ~50 000 pairs / second on an RTX 5080
  * Input pair: (``"Does this post reference {name}?"``,  ``post_text[:512]``)
  * Output: raw logit → sigmoid → confidence in [0, 1]

``is_oblique`` heuristic
  ``True`` when ``match_type`` ∈ {``semantic``, ``phonetic_skeleton``}: these
  represent indirect or encoded references rather than direct name mentions.

Cache
  Scored results written to ``data/processed/adjudication_cache.parquet``
  keyed on ``(post_id, attacker_id, model_name)``.  Already-scored rows are
  skipped on re-runs for reproducibility.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
import polars as pl

from saints_score.logging import logger

if TYPE_CHECKING:
    from saints_score.config import Settings

# ── Constants ────────────────────────────────────────────────────────────

# Match types accepted with confidence=1.0 without model scoring.
_EXACT_MATCH_TYPES: frozenset[str] = frozenset({"exact_substring"})

# Match types whose is_oblique flag is set to True (indirect references).
_OBLIQUE_MATCH_TYPES: frozenset[str] = frozenset({"semantic", "phonetic_skeleton"})

# Characters of post text sent to the cross-encoder per pair.
_POST_TEXT_LIMIT: int = 512

# ── Module-level model cache ─────────────────────────────────────────────

_model_cache: dict[str, Any] = {}


# ── Resource management ──────────────────────────────────────────────────


def release_cross_encoder_resources() -> None:
    """Release cached cross-encoder model and free GPU memory."""
    _model_cache.clear()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


# ── Internal helpers ─────────────────────────────────────────────────────


def _sigmoid(x: np.ndarray) -> np.ndarray:
    """Element-wise sigmoid, clipped to avoid float64 overflow."""
    x = np.asarray(x, dtype=np.float64)
    return 1.0 / (1.0 + np.exp(-np.clip(x, -500.0, 500.0)))


def _get_cross_encoder(cfg: Settings) -> Any:
    """Load (or return cached) CrossEncoder on the best available device."""
    import torch
    from sentence_transformers import CrossEncoder

    key = cfg.cross_encoder_model
    if key not in _model_cache:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info("Loading cross-encoder {} on {}", key, device)
        _model_cache[key] = CrossEncoder(key, device=device, max_length=512)
    return _model_cache[key]


def _cache_path(cfg: Settings) -> Path:
    return cfg.resolve(cfg.data_processed) / "adjudication_cache.parquet"


def _load_cache(cache_path: Path) -> pl.DataFrame:
    """Load parquet adjudication cache; return empty frame if absent."""
    if cache_path.exists():
        try:
            return pl.read_parquet(cache_path)
        except Exception as e:
            logger.warning("Could not load adjudication cache ({}). Starting fresh.", e)
    return pl.DataFrame(
        schema={
            "post_id": pl.Int64,
            "attacker_id": pl.Utf8,
            "model_name": pl.Utf8,
            "confidence": pl.Float64,
        }
    )


def _save_cache(cache_df: pl.DataFrame, cache_path: Path) -> None:
    """Persist adjudication cache as parquet (atomic write via tmp file)."""
    import io

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    cache_df.write_parquet(buf)
    tmp = cache_path.with_suffix(".tmp.parquet")
    tmp.write_bytes(buf.getvalue())
    tmp.replace(cache_path)


# ── Public API ───────────────────────────────────────────────────────────


def adjudicate_candidates(
    candidates: pl.DataFrame,
    posts: pl.DataFrame,
    cases: pl.DataFrame,
    cfg: Settings,
    *,
    batch_size: int | None = None,
    max_candidates: int | None = None,
) -> pl.DataFrame:
    """Adjudicate mention candidates using a GPU cross-encoder.

    Strategy
    --------
    ``exact_substring`` candidates are accepted unconditionally (confidence=1.0).
    All other candidates (fuzzy, adversarial, phonetic, semantic) are scored by
    the cross-encoder; those with sigmoid(logit) ≥ ``mention_confidence_threshold``
    are marked as references.

    The exact-match tier is processed with vectorised Polars to handle the
    ~19.8 M rows without Python-level iteration.  Only the much smaller
    non-exact subset (~186 K rows) is iterated in Python for inference.

    Parameters
    ----------
    candidates:
        DataFrame with at minimum ``post_id``, ``attacker_id``, ``match_type``.
        An ``alias_matched`` column is used when present.
    posts:
        Posts DataFrame with ``post_id`` and ``body_clean`` (or ``body``) cols.
    cases:
        Cases DataFrame for attacker name lookup.
    cfg:
        Pipeline settings.
    batch_size:
        Override cross-encoder prediction batch size (default from config).
    max_candidates:
        Cap total candidates; useful for smoke-testing.

    Returns
    -------
    DataFrame with columns:
        ``post_id``, ``attacker_id``, ``is_reference``, ``confidence``,
        ``inferred_alias``, ``is_oblique``, ``source_stage``, ``alias_matched``
    """
    if max_candidates:
        candidates = candidates.head(max_candidates)

    # Ensure alias_matched column exists
    if "alias_matched" not in candidates.columns:
        candidates = candidates.with_columns(pl.lit("").alias("alias_matched"))

    # Build attacker name lookup
    attacker_name: dict[str, str] = {}
    for row in cases.iter_rows(named=True):
        cid = row["case_id"]
        attacker_name[cid] = (
            row.get("perpetrator_name") or row.get("perp_name") or cid
        )

    # Build post text lookup (prefer body_clean, fall back to body)
    candidate_pids = candidates["post_id"].unique()
    text_col = "body_clean" if "body_clean" in posts.columns else "body"
    fallback_col = "body" if text_col == "body_clean" and "body" in posts.columns else None
    relevant_posts = posts.filter(pl.col("post_id").is_in(candidate_pids))
    post_text: dict[int, str] = {}
    for row in relevant_posts.iter_rows(named=True):
        t = row.get(text_col) or (row.get(fallback_col) if fallback_col else None) or ""
        if t:
            post_text[int(row["post_id"])] = t

    # ── Tier 1: exact_substring — vectorised accept ───────────────────
    has_match_type = "match_type" in candidates.columns
    if has_match_type:
        exact_mask = candidates["match_type"].is_in(list(_EXACT_MATCH_TYPES))
        exact_df = candidates.filter(exact_mask)
        verify_df = candidates.filter(~exact_mask)
    else:
        exact_df = candidates
        verify_df = pl.DataFrame(schema=candidates.schema)

    logger.info(
        "Adjudication: {} exact (auto-accept), {} queued for cross-encoder",
        exact_df.height,
        verify_df.height,
    )

    frames: list[pl.DataFrame] = []

    if exact_df.height > 0:
        oblique_types = list(_OBLIQUE_MATCH_TYPES)
        exact_results = exact_df.select([
            pl.col("post_id"),
            pl.col("attacker_id"),
            pl.lit(True).alias("is_reference"),
            pl.lit(1.0).cast(pl.Float64).alias("confidence"),
            pl.col("alias_matched").alias("inferred_alias"),
            pl.col("match_type").is_in(oblique_types).alias("is_oblique"),
            pl.col("match_type").alias("source_stage"),
            pl.col("alias_matched"),
        ])
        frames.append(exact_results)

    # ── Tier 2: cross-encoder scoring ─────────────────────────────────
    if verify_df.height > 0:
        model_name = cfg.cross_encoder_model
        cache_p = _cache_path(cfg)
        cache_df = _load_cache(cache_p)

        # Lookup existing cached scores for this model
        if cache_df.height > 0 and "model_name" in cache_df.columns:
            cached_for_model = cache_df.filter(pl.col("model_name") == model_name)
        else:
            cached_for_model = pl.DataFrame(
                schema={"post_id": pl.Int64, "attacker_id": pl.Utf8,
                        "model_name": pl.Utf8, "confidence": pl.Float64}
            )

        conf_lookup: dict[tuple[int, str], float] = {
            (int(r["post_id"]), r["attacker_id"]): float(r["confidence"])
            for r in cached_for_model.iter_rows(named=True)
        }

        # Split verify_df into already-cached vs needs-inference
        cached_verify_rows: list[dict[str, Any]] = []
        to_score_rows: list[dict[str, Any]] = []
        for row in verify_df.iter_rows(named=True):
            key = (int(row["post_id"]), row["attacker_id"])
            if key in conf_lookup:
                cached_verify_rows.append({**row, "_cached_conf": conf_lookup[key]})
            else:
                to_score_rows.append(row)

        logger.info(
            "Cross-encoder: {} cached hits, {} new pairs to score",
            len(cached_verify_rows),
            len(to_score_rows),
        )

        # Emit cached hits
        if cached_verify_rows:
            verify_cache_results: list[dict[str, Any]] = []
            for row in cached_verify_rows:
                conf = row["_cached_conf"]
                mtype = row.get("match_type", "unknown")
                verify_cache_results.append({
                    "post_id": row["post_id"],
                    "attacker_id": row["attacker_id"],
                    "is_reference": conf >= cfg.mention_confidence_threshold,
                    "confidence": conf,
                    "inferred_alias": row.get("alias_matched") or None,
                    "is_oblique": mtype in _OBLIQUE_MATCH_TYPES,
                    "source_stage": mtype,
                    "alias_matched": row.get("alias_matched", ""),
                })
            frames.append(pl.DataFrame(verify_cache_results))

        # Score new pairs
        if to_score_rows:
            effective_batch = batch_size or cfg.cross_encoder_batch_size

            pairs: list[list[str]] = []
            valid_rows: list[dict[str, Any]] = []
            no_text_results: list[dict[str, Any]] = []

            for row in to_score_rows:
                pid = int(row["post_id"])
                aid = row["attacker_id"]
                text = post_text.get(pid, "")[:_POST_TEXT_LIMIT]
                if not text:
                    no_text_results.append({
                        "post_id": row["post_id"],
                        "attacker_id": aid,
                        "is_reference": False,
                        "confidence": 0.0,
                        "inferred_alias": None,
                        "is_oblique": False,
                        "source_stage": row.get("match_type", "unknown"),
                        "alias_matched": row.get("alias_matched", ""),
                    })
                    continue
                name = attacker_name.get(aid, aid)
                query = f"Does this post reference or mention {name}?"
                pairs.append([query, text])
                valid_rows.append(row)

            if no_text_results:
                frames.append(pl.DataFrame(no_text_results))

            if pairs:
                model = _get_cross_encoder(cfg)
                logger.info(
                    "Running cross-encoder on {} pairs (batch_size={})",
                    len(pairs),
                    effective_batch,
                )
                logits = model.predict(
                    pairs,
                    batch_size=effective_batch,
                    show_progress_bar=len(pairs) > 1000,
                )
                confidences = _sigmoid(np.asarray(logits, dtype=np.float64))

                scored_results: list[dict[str, Any]] = []
                new_cache_rows: list[dict[str, Any]] = []
                for row, conf in zip(valid_rows, confidences):
                    pid = row["post_id"]
                    aid = row["attacker_id"]
                    mtype = row.get("match_type", "unknown")
                    conf_f = float(conf)
                    scored_results.append({
                        "post_id": pid,
                        "attacker_id": aid,
                        "is_reference": conf_f >= cfg.mention_confidence_threshold,
                        "confidence": conf_f,
                        "inferred_alias": row.get("alias_matched") or None,
                        "is_oblique": mtype in _OBLIQUE_MATCH_TYPES,
                        "source_stage": mtype,
                        "alias_matched": row.get("alias_matched", ""),
                    })
                    new_cache_rows.append({
                        "post_id": pid,
                        "attacker_id": aid,
                        "model_name": model_name,
                        "confidence": conf_f,
                    })

                frames.append(pl.DataFrame(scored_results))

                # Persist updated cache
                updated_cache = pl.concat(
                    [cache_df, pl.DataFrame(new_cache_rows)],
                    how="diagonal_relaxed",
                ).unique(subset=["post_id", "attacker_id", "model_name"])
                _save_cache(updated_cache, cache_p)
                logger.info(
                    "Cross-encoder: scored {} new pairs, cache saved to {}",
                    len(new_cache_rows),
                    cache_p,
                )

    _EMPTY_SCHEMA: dict[str, type[pl.DataType]] = {
        "post_id": pl.Int64,
        "attacker_id": pl.Utf8,
        "is_reference": pl.Boolean,
        "confidence": pl.Float64,
        "inferred_alias": pl.Utf8,
        "is_oblique": pl.Boolean,
        "source_stage": pl.Utf8,
        "alias_matched": pl.Utf8,
    }

    if not frames:
        return pl.DataFrame(schema=_EMPTY_SCHEMA)

    result = pl.concat(frames, how="diagonal_relaxed")
    logger.info("Adjudication complete: {} total results", result.height)
    return result


def filter_mentions(
    adjudicated: pl.DataFrame,
    cfg: Settings,
) -> pl.DataFrame:
    """Filter adjudicated candidates to final confirmed mentions.

    Applies the confidence threshold and ``is_reference`` flag.
    """
    mentions = adjudicated.filter(
        (pl.col("is_reference") == True)  # noqa: E712
        & (pl.col("confidence") >= cfg.mention_confidence_threshold)
    )
    logger.info(
        "Filtered to {} mentions (threshold: {})",
        mentions.height,
        cfg.mention_confidence_threshold,
    )
    return mentions
