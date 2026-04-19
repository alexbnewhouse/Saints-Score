"""Candidate retrieval — semantic similarity (§6.2 stage 3).

Embeds posts and attacker probes, retrieves nearest neighbours.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import polars as pl

from saints_score.logging import logger

if TYPE_CHECKING:
    from saints_score.config import Settings


def build_attacker_probes(cases: pl.DataFrame) -> dict[str, list[str]]:
    """Build short natural-language probes per attacker for semantic retrieval.

    E.g., "a post referring to the 2019 Christchurch mosque shooter".
    """
    probes: dict[str, list[str]] = {}
    for row in cases.iter_rows(named=True):
        case_id = row["case_id"]
        name = row.get("perpetrator_name") or row.get("perp_name") or ""
        year = row.get("event_year") or ""
        country = row.get("country") or ""
        venue = row.get("venue_type") or ""

        case_probes = [
            f"a post referring to the {year} {country} mass shooting by {name}",
            f"a discussion about {name} the shooter",
            f"celebrating or mourning the {year} {country} attack",
        ]
        if venue:
            case_probes.append(f"a post about the {venue} attack in {country}")

        probes[case_id] = case_probes

    return probes


def embed_texts(
    texts: list[str],
    cfg: Settings,
    *,
    batch_size: int | None = None,
    show_progress: bool = True,
) -> np.ndarray:
    """Embed texts using the configured sentence-transformer model.

    Returns an (N, D) float32 array.
    """
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(
        cfg.embedding_model,
        revision=cfg.embedding_revision or None,
        trust_remote_code=True,
    )
    bs = batch_size or cfg.embedding_batch_size
    logger.info("Embedding {} texts with {} (batch_size={})", len(texts), cfg.embedding_model, bs)

    embeddings = model.encode(
        texts,
        batch_size=bs,
        show_progress_bar=show_progress,
        normalize_embeddings=True,
    )
    return np.asarray(embeddings, dtype=np.float32)


def semantic_candidate_retrieval(
    post_embeddings: np.ndarray,
    post_ids: list[int],
    probes: dict[str, list[str]],
    cfg: Settings,
) -> pl.DataFrame:
    """Retrieve top-k semantically similar posts for each attacker.

    Parameters
    ----------
    post_embeddings:
        (N, D) normalised embedding matrix for posts.
    post_ids:
        Corresponding post IDs.
    probes:
        Attacker ID → list of probe sentences.
    cfg:
        Pipeline settings.

    Returns
    -------
    DataFrame with columns: ``post_id``, ``attacker_id``, ``similarity``,
    ``match_type``.
    """
    results: list[dict] = []

    for attacker_id, probe_texts in probes.items():
        probe_emb = embed_texts(probe_texts, cfg, show_progress=False)
        # Mean of probe embeddings as the attacker centroid
        centroid = probe_emb.mean(axis=0)
        centroid /= np.linalg.norm(centroid)

        # Cosine similarity (embeddings already normalised)
        sims = post_embeddings @ centroid
        topk_idx = np.argsort(sims)[-cfg.semantic_topk:][::-1]

        for idx in topk_idx:
            results.append({
                "post_id": post_ids[idx],
                "attacker_id": attacker_id,
                "similarity": float(sims[idx]),
                "match_type": "semantic",
            })

    if not results:
        return pl.DataFrame(
            schema={
                "post_id": pl.Int64,
                "attacker_id": pl.Utf8,
                "similarity": pl.Float64,
                "match_type": pl.Utf8,
            }
        )

    df = pl.DataFrame(results)
    logger.info("Semantic retrieval: {} candidates across {} attackers",
                df.height, df["attacker_id"].n_unique())
    return df
