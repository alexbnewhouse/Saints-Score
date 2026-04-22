"""Centralised configuration via Pydantic Settings.

All paths, model IDs, window widths, seeds, and tuning parameters live here.
Override via environment variables (prefixed ``SAINTS_``) or a ``config.toml``.
"""

from __future__ import annotations

import tomllib  # type: ignore[import-untyped]
from pathlib import Path
from typing import Any

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_toml(path: Path) -> dict[str, Any]:
    """Load a TOML file and return the ``[saints_score]`` table (or empty dict)."""
    if not path.is_file():
        return {}
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return data.get("saints_score", {})


class Settings(BaseSettings):
    """Pipeline-wide configuration."""

    model_config = SettingsConfigDict(
        env_prefix="SAINTS_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # ── Reproducibility ──────────────────────────────────────────────
    seed: int = 20260414

    # ── Paths ────────────────────────────────────────────────────────
    project_root: Path = PROJECT_ROOT
    data_raw: Path = Field(default=Path("data/raw"))
    data_interim: Path = Field(default=Path("data/interim"))
    data_processed: Path = Field(default=Path("data/processed"))
    out_dir: Path = Field(default=Path("out"))
    run_log_dir: Path = Field(default=Path("out/runs"))

    # ── /pol/ ingest ─────────────────────────────────────────────────
    pol_tar_path: Path = Field(default=Path("data/pol/pol.csv.tar.gz"))
    pol_parquet_dir: Path = Field(default=Path("data/interim/pol"))
    ingest_chunk_size: int = 1_000_000

    # ── Cases ────────────────────────────────────────────────────────
    cases_csv_path: Path = Field(default=Path("out/cases_audited.csv"))

    # ── Embedding model ──────────────────────────────────────────────
    embedding_model: str = "nomic-ai/nomic-embed-text-v1.5"
    embedding_revision: str = ""
    embedding_batch_size: int = 256

    # ── Cross-encoder adjudicator ────────────────────────────────────
    cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    cross_encoder_batch_size: int = 512

    # ── Sentiment / Emotion models ───────────────────────────────────
    sentiment_model: str = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
    emotion_model: str = "SamLowe/roberta-base-go_emotions"
    toxicity_model: str = "unitary/unbiased-toxic-roberta"

    # ── Temporal windows (days) ──────────────────────────────────────
    baseline_start: int = -365
    baseline_end: int = -1
    immediate_start: int = 0
    immediate_end: int = 7
    nearterm_start: int = 8
    nearterm_end: int = 90
    longterm_start: int = 91
    longterm_end: int = 730

    # ── Mention detection ────────────────────────────────────────────
    fuzzy_threshold: int = 85
    semantic_topk: int = 500
    min_alias_token_len: int = 4
    max_bootstrap_rounds: int = 3
    mention_confidence_threshold: float = 0.5

    # ── Scoring ──────────────────────────────────────────────────────
    epsilon: float = 1e-6

    # ── Helpers ──────────────────────────────────────────────────────

    @model_validator(mode="before")
    @classmethod
    def _merge_toml(cls, values: dict[str, Any]) -> dict[str, Any]:
        """If a ``config_path`` env var / init kwarg is set, merge the TOML."""
        config_path = values.pop("config_path", None)
        if config_path is not None:
            toml_vals = _load_toml(Path(config_path))
            # TOML values are low-priority defaults; explicit values win
            for k, v in toml_vals.items():
                values.setdefault(k, v)
        return values

    def resolve(self, p: Path) -> Path:
        """Resolve a relative path against *project_root*."""
        if p.is_absolute():
            return p
        return self.project_root / p

    @property
    def pol_tar(self) -> Path:
        return self.resolve(self.pol_tar_path)

    @property
    def pol_parquet(self) -> Path:
        return self.resolve(self.pol_parquet_dir)

    @property
    def interim(self) -> Path:
        return self.resolve(self.data_interim)

    @property
    def processed(self) -> Path:
        return self.resolve(self.data_processed)

    @property
    def raw(self) -> Path:
        return self.resolve(self.data_raw)

    @property
    def out(self) -> Path:
        return self.resolve(self.out_dir)

    @property
    def runs(self) -> Path:
        return self.resolve(self.run_log_dir)


def get_settings(config_path: str | Path | None = None) -> Settings:
    """Factory: load settings, optionally from a TOML file."""
    kwargs: dict[str, Any] = {}
    if config_path is not None:
        kwargs["config_path"] = str(config_path)
    return Settings(**kwargs)
