"""Affective scoring: sentiment, emotion, and toxicity classification.

Runs transformer classifiers on mention-set posts (§6.3).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import polars as pl
import torch
from transformers import pipeline

from saints_score.io.parquet import write_parquet
from saints_score.logging import logger

if TYPE_CHECKING:
    from saints_score.config import Settings


def _get_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def score_sentiment(
    posts: pl.DataFrame,
    cfg: Settings,
    *,
    batch_size: int = 64,
    text_col: str = "body",
) -> pl.DataFrame:
    """Run 3-way sentiment classification on posts.

    Returns DataFrame with ``post_id``, ``sentiment_label``, ``sentiment_score``,
    and per-class probabilities.
    """
    device = _get_device()
    logger.info("Loading sentiment model: {} (device: {})", cfg.sentiment_model, device)

    pipe = pipeline(
        "sentiment-analysis",
        model=cfg.sentiment_model,
        device=device,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        truncation=True,
        max_length=512,
    )

    texts = posts.select(text_col).to_series().to_list()
    post_ids = posts.select("post_id").to_series().to_list()

    logger.info("Scoring sentiment on {} posts", len(texts))
    results = pipe(texts, batch_size=batch_size, top_k=None)

    records: list[dict[str, Any]] = []
    for pid, result in zip(post_ids, results, strict=True):
        row: dict[str, Any] = {"post_id": pid}
        best_label = ""
        best_score = 0.0
        for item in result:
            label = item["label"].lower()
            score = item["score"]
            row[f"sentiment_{label}"] = score
            if score > best_score:
                best_score = score
                best_label = label
        row["sentiment_label"] = best_label
        row["sentiment_score"] = best_score
        records.append(row)

    return pl.DataFrame(records)


def score_emotion(
    posts: pl.DataFrame,
    cfg: Settings,
    *,
    batch_size: int = 64,
    text_col: str = "body",
) -> pl.DataFrame:
    """Run 27-emotion multilabel classification (GoEmotions).

    Returns DataFrame with ``post_id`` and one column per emotion label.
    """
    device = _get_device()
    logger.info("Loading emotion model: {} (device: {})", cfg.emotion_model, device)

    pipe = pipeline(
        "text-classification",
        model=cfg.emotion_model,
        device=device,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        truncation=True,
        max_length=512,
        top_k=None,
    )

    texts = posts.select(text_col).to_series().to_list()
    post_ids = posts.select("post_id").to_series().to_list()

    logger.info("Scoring emotion on {} posts", len(texts))
    results = pipe(texts, batch_size=batch_size)

    records: list[dict[str, Any]] = []
    for pid, result in zip(post_ids, results, strict=True):
        row: dict[str, Any] = {"post_id": pid}
        for item in result:
            label = item["label"].lower().replace(" ", "_")
            row[f"emotion_{label}"] = item["score"]
        records.append(row)

    return pl.DataFrame(records)


def score_toxicity(
    posts: pl.DataFrame,
    cfg: Settings,
    *,
    batch_size: int = 64,
    text_col: str = "body",
) -> pl.DataFrame:
    """Run toxicity classification as a control covariate.

    Returns DataFrame with ``post_id`` and toxicity scores.
    """
    device = _get_device()
    logger.info("Loading toxicity model: {} (device: {})", cfg.toxicity_model, device)

    pipe = pipeline(
        "text-classification",
        model=cfg.toxicity_model,
        device=device,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        truncation=True,
        max_length=512,
        top_k=None,
    )

    texts = posts.select(text_col).to_series().to_list()
    post_ids = posts.select("post_id").to_series().to_list()

    logger.info("Scoring toxicity on {} posts", len(texts))
    results = pipe(texts, batch_size=batch_size)

    records: list[dict[str, Any]] = []
    for pid, result in zip(post_ids, results, strict=True):
        row: dict[str, Any] = {"post_id": pid}
        for item in result:
            label = item["label"].lower().replace(" ", "_")
            row[f"toxicity_{label}"] = item["score"]
        records.append(row)

    return pl.DataFrame(records)


def run_affect_pipeline(
    mentions: pl.DataFrame,
    posts: pl.DataFrame,
    cfg: Settings,
) -> pl.DataFrame:
    """Full affect pipeline: join mentions with posts, score all three models.

    Returns a single DataFrame with all affect scores per post.
    """
    # Get unique post IDs from mentions
    mention_pids = mentions.select("post_id").unique()
    mention_posts = posts.join(mention_pids, on="post_id")
    logger.info("Scoring affect on {} mention posts", mention_posts.height)

    sentiment_df = score_sentiment(mention_posts, cfg)
    emotion_df = score_emotion(mention_posts, cfg)
    toxicity_df = score_toxicity(mention_posts, cfg)

    # Join all scores
    affect = sentiment_df.join(emotion_df, on="post_id").join(toxicity_df, on="post_id")

    # Write
    out_path = cfg.resolve(cfg.data_processed) / "affect_scores.parquet"
    write_parquet(affect, out_path)

    return affect
