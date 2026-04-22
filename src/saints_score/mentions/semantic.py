"""Candidate retrieval — semantic similarity (§6.2 stage 3).

Embeds posts and attacker probes, retrieves nearest neighbours.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import polars as pl

from saints_score.logging import logger

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

    from saints_score.config import Settings

# Module-level model cache to avoid reloading per call.
_model_cache: dict[str, SentenceTransformer] = {}


def release_embedding_resources() -> None:
    """Release cached embedding model and free accelerator memory."""
    _model_cache.clear()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        # Best-effort cleanup only.
        pass


def _get_embedding_model(cfg: Settings) -> SentenceTransformer:
    """Load (or return cached) SentenceTransformer model.

    When CUDA is available, the model is loaded in float16 for ~2× throughput.
    """
    import torch
    from sentence_transformers import SentenceTransformer

    key = f"{cfg.embedding_model}:{cfg.embedding_revision}"
    if key not in _model_cache:
        kwargs: dict[str, object] = {}
        if torch.cuda.is_available():
            kwargs["device"] = "cuda"
            kwargs["model_kwargs"] = {"torch_dtype": torch.float16}
            logger.info("Loading embedding model on CUDA with float16")
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            kwargs["device"] = "mps"
        _model_cache[key] = SentenceTransformer(
            cfg.embedding_model,
            revision=cfg.embedding_revision or None,
            **kwargs,
        )
    return _model_cache[key]


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

    Uses ``cfg.embedding_batch_size`` by default. On GPU, applies a conservative
    VRAM-based safety cap to avoid OOMs on large corpora.

    Returns an (N, D) float32 array.
    """
    import torch

    model = _get_embedding_model(cfg)
    bs = batch_size or cfg.embedding_batch_size
    if batch_size is None and torch.cuda.is_available():
        dev = torch.cuda.current_device()
        mem_gb = torch.cuda.get_device_properties(dev).total_memory / (1024**3)
        # Safety cap only (do not auto-increase): keeps config-driven defaults stable.
        # Empirically conservative for nomic-embed-text-v1.5 on 16GB-class GPUs.
        safe_cap = max(32, min(int(mem_gb * 16), 512))
        if bs > safe_cap:
            logger.warning(
                "GPU detected ({:.1f} GB VRAM): reducing batch_size {} -> {} for stability",
                mem_gb,
                bs,
                safe_cap,
            )
            bs = safe_cap
        else:
            logger.info("GPU detected ({:.1f} GB VRAM): using batch_size={}", mem_gb, bs)

    # Cap per-post sequence length: nomic-embed-text-v1.5 defaults to 8192 tokens,
    # which causes OOM in RoPE attention intermediates even at modest batch sizes.
    # /pol/ posts fit comfortably within 512 tokens (~384 words).
    _MAX_SEQ_LEN = 512
    if hasattr(model, "max_seq_length") and model.max_seq_length > _MAX_SEQ_LEN:
        logger.info(
            "Capping model max_seq_length {} -> {} to reduce VRAM usage",
            model.max_seq_length,
            _MAX_SEQ_LEN,
        )
        model.max_seq_length = _MAX_SEQ_LEN

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
        topk_idx = np.argsort(sims)[-cfg.semantic_topk :][::-1]

        for idx in topk_idx:
            results.append(
                {
                    "post_id": post_ids[idx],
                    "attacker_id": attacker_id,
                    "similarity": float(sims[idx]),
                    "match_type": "semantic",
                }
            )

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
    logger.info(
        "Semantic retrieval: {} candidates across {} attackers",
        df.height,
        df["attacker_id"].n_unique(),
    )
    return df
