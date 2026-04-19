"""Seed alias inventory for attacker mention detection.

Assembles, persists, and manages the initial alias list per attacker.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import polars as pl

from saints_score.io.parquet import read_parquet, write_parquet
from saints_score.logging import logger

if TYPE_CHECKING:
    from pathlib import Path

    from saints_score.config import Settings


def build_seed_aliases(cases: pl.DataFrame) -> pl.DataFrame:
    """Build the seed alias inventory from case metadata.

    For each attacker extracts:
    - Canonical perpetrator name
    - Known aliases from ``perp_aliases`` field (semicolon-separated)
    - Last-name-only variant
    - Common misspellings / abbreviations where obvious

    Returns a DataFrame with columns: ``attacker_id``, ``alias``, ``source``.
    """
    records: list[dict[str, str]] = []

    for row in cases.iter_rows(named=True):
        case_id = row["case_id"]
        perp_name = row.get("perpetrator_name") or row.get("perp_name")
        if not perp_name:
            continue

        # Canonical name
        records.append(
            {
                "attacker_id": case_id,
                "alias": perp_name.strip(),
                "source": "canonical_name",
            }
        )

        # Last name only (if multi-word)
        parts = perp_name.strip().split()
        if len(parts) >= 2:
            records.append(
                {
                    "attacker_id": case_id,
                    "alias": parts[-1],
                    "source": "last_name",
                }
            )

        # Known aliases field
        aliases_raw = row.get("perp_aliases") or row.get("aliases")
        if aliases_raw:
            for alias in str(aliases_raw).split(";"):
                alias = alias.strip()
                if alias and alias.lower() not in ("null", "none", "n/a"):
                    records.append(
                        {
                            "attacker_id": case_id,
                            "alias": alias,
                            "source": "case_metadata",
                        }
                    )

        # Online handles
        handles = row.get("primary_online_handles")
        if handles:
            for handle in str(handles).split(";"):
                handle = handle.strip()
                if handle and handle.lower() not in ("null", "none", "n/a"):
                    records.append(
                        {
                            "attacker_id": case_id,
                            "alias": handle,
                            "source": "online_handle",
                        }
                    )

    if not records:
        return pl.DataFrame(schema={"attacker_id": pl.Utf8, "alias": pl.Utf8, "source": pl.Utf8})

    df = pl.DataFrame(records)
    # Deduplicate
    df = df.unique(subset=["attacker_id", "alias"])
    logger.info(
        "Built seed alias inventory: {} aliases for {} attackers",
        df.height,
        df["attacker_id"].n_unique(),
    )
    return df


def save_seed_aliases(aliases: pl.DataFrame, cfg: Settings) -> Path:
    """Persist seed aliases to Parquet."""
    path = cfg.resolve(cfg.data_processed) / "aliases_seed.parquet"
    write_parquet(aliases, path)
    return path


def load_seed_aliases(cfg: Settings) -> pl.DataFrame:
    """Load the persisted seed alias inventory."""
    path = cfg.resolve(cfg.data_processed) / "aliases_seed.parquet"
    return read_parquet(path)
