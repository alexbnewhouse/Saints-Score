"""Load, validate, and write the attack-case dataset.

Reads ``cases_audited.csv`` (produced by convert.py), validates with Pandera,
and writes ``data/processed/cases.parquet``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandera.polars as pa
import polars as pl

from saints_score.io.parquet import write_parquet
from saints_score.logging import logger

if TYPE_CHECKING:
    from saints_score.config import Settings

# ── Pandera schema for the cases dataset ───────────────────────────────────

VALID_STATUSES = {"C", "PF", "F"}
VALID_METHODS = {"firearm", "vehicle", "blade", "arson", "explosive", "mixed", "other"}
VALID_RELEVANCE = {"low", "medium", "medium_high", "high", "very_high", "contested"}
VALID_TRADITIONS = {
    "core_farright", "incel", "kolumbayn", "columbine_fandom",
    "tcc", "jihadist", "mixed", "none", "misc",
}


class CaseSchema(pa.DataFrameModel):
    """Pandera schema for the cases dataset."""

    case_id: str = pa.Field(nullable=False, unique=True)
    event_date: str = pa.Field(nullable=True)  # validated as date post-load
    event_year: int = pa.Field(ge=2001, le=2027, nullable=True)
    country: str = pa.Field(nullable=False)
    status: str = pa.Field(isin=list(VALID_STATUSES), nullable=True)

    class Config:
        strict = False  # allow extra columns
        coerce = True


def load_cases(cfg: Settings) -> pl.DataFrame:
    """Load and validate the case dataset.

    Returns the validated DataFrame.  Reports any validation issues via logger.
    """
    csv_path = cfg.resolve(cfg.cases_csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Cases CSV not found: {csv_path}")

    logger.info("Loading cases from {}", csv_path)
    df = pl.read_csv(csv_path, infer_schema_length=0)  # all strings initially
    logger.info("Loaded {} cases, {} columns", df.height, df.width)

    # Type coercions
    int_cols = [
        "event_year", "perp_age", "fatalities_total_incl_perp",
        "fatalities_excl_perp", "total_casualties",
        "incoming_citation_count", "outgoing_citation_count",
        "manifesto_length_pages", "livestream_duration_min",
        "evidence_tier",
    ]
    for col in int_cols:
        if col in df.columns:
            df = df.with_columns(pl.col(col).cast(pl.Int64, strict=False))

    # Date parsing
    if "event_date" in df.columns:
        df = df.with_columns(
            pl.col("event_date").str.to_date("%Y-%m-%d", strict=False)
        )

    # Validate required fields
    missing_case_id = df.filter(pl.col("case_id").is_null()).height
    if missing_case_id:
        logger.warning("{} rows have null case_id", missing_case_id)

    missing_country = df.filter(pl.col("country").is_null()).height
    if missing_country:
        logger.warning("{} rows have null country", missing_country)

    # Check year range
    if "event_year" in df.columns:
        year_range = df.select(
            pl.col("event_year").min().alias("min_year"),
            pl.col("event_year").max().alias("max_year"),
        ).row(0)
        logger.info("Year range: {} - {}", year_range[0], year_range[1])

    # Check duplicate case_ids
    dupes = df.group_by("case_id").count().filter(pl.col("count") > 1)
    if dupes.height > 0:
        logger.warning("Duplicate case_ids: {}", dupes["case_id"].to_list())

    return df


def process_cases(cfg: Settings) -> tuple[pl.DataFrame, dict[str, Any]]:
    """Load, validate, and persist the case dataset.

    Returns (DataFrame, report_dict).
    """
    df = load_cases(cfg)

    report: dict[str, Any] = {
        "n_cases": df.height,
        "n_columns": df.width,
        "columns": df.columns,
    }

    if "status" in df.columns:
        status_counts = df.group_by("status").count().sort("status")
        report["status_distribution"] = {
            r["status"]: r["count"] for r in status_counts.iter_rows(named=True)
        }

    if "saints_relevance" in df.columns:
        rel_counts = df.group_by("saints_relevance").count().sort("saints_relevance")
        report["relevance_distribution"] = {
            r["saints_relevance"]: r["count"] for r in rel_counts.iter_rows(named=True)
        }

    # Write processed Parquet
    out_path = cfg.resolve(cfg.data_processed) / "cases.parquet"
    write_parquet(df, out_path)
    logger.info("Cases written → {}", out_path)

    return df, report
