"""Ingest /pol/ CSV tar.gz → partitioned Parquet.

Implements Phase 1 (§6.1): stream-decompress, parse, normalise, partition by
(year, month), compute corpus manifest.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import unicodedata
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import polars as pl

from saints_score.io.parquet import write_partitioned
from saints_score.io.tar_stream import iter_tar_csv_chunks
from saints_score.logging import logger

if TYPE_CHECKING:
    from saints_score.config import Settings

# ── 4plebs CSV column mapping ──────────────────────────────────────────────
# Columns from the 4plebs /pol/ dump (positions based on sample_header.txt)
FOURPLEBS_COLS = [
    "num",  # 0  — post number (globally unique)
    "subnum",  # 1
    "thread_num",  # 2  — thread OP number
    "op",  # 3  — 1 if OP, 0 otherwise
    "timestamp",  # 4  — unix epoch
    "fourchan_date",  # 5
    "name",  # 6
    "email",  # 7
    "trip",  # 8
    "title",  # 9
    "comment",  # 10  — raw HTML post body
    "poster_hash",  # 11 — ephemeral per-thread poster ID
    "poster_country",  # 12
    "media_filename",  # 13
    "media_w",  # 14
    "media_h",  # 15
    "preview_orig",  # 16
    "preview_w",  # 17
    "preview_h",  # 18
    "media_hash",  # 19
    "media_orig",  # 20
    "spoiler",  # 21
    "deleted",  # 22
    "capcode",  # 23
    "exif",  # 24
    "sticky",  # 25
    "since4pass",  # 26
]

# Indices we actually need
IDX_NUM = 0
IDX_THREAD = 2
IDX_TIMESTAMP = 4
IDX_TITLE = 9
IDX_COMMENT = 10
IDX_POSTER_HASH = 11
IDX_COUNTRY = 12
IDX_MEDIA_ORIG = 20

# HTML tag stripper
_TAG_RE = re.compile(r"<[^>]+>")
# >>NNN reply extractor
_REPLY_RE = re.compile(r">>(\d+)")
# Whitespace normaliser
_WS_RE = re.compile(r"\s+")
# Greentext arrows for cleaning
_GT_RE = re.compile(r"^>{1,3}\s*", re.MULTILINE)


def _strip_html(text: str) -> str:
    """Remove HTML tags, decode entities, strip leading/trailing whitespace."""
    text = html.unescape(text)
    text = _TAG_RE.sub(" ", text)
    return text.strip()


def _clean_body(text: str) -> str:
    """Additional normalisation for the ``body_clean`` column.

    - NFKC unicode normalisation
    - Lowercase
    - Collapse whitespace
    - Strip greentext arrows
    """
    text = unicodedata.normalize("NFKC", text)
    text = text.lower()
    text = _GT_RE.sub("", text)
    text = _WS_RE.sub(" ", text)
    return text.strip()


def _extract_replies(text: str) -> list[int]:
    """Extract ``>>NNN`` reply references from raw post text."""
    return [int(m) for m in _REPLY_RE.findall(text)]


def _safe_int(val: str) -> int | None:
    """Parse a string to int, returning None for \\N or empty."""
    if not val or val == "\\N" or val == "N":
        return None
    try:
        return int(val)
    except ValueError:
        return None


def _safe_str(val: str) -> str | None:
    """Convert \\N to None, empty to None."""
    if not val or val == "\\N":
        return None
    return val


def parse_chunk(rows: list[list[str]]) -> pl.DataFrame:
    """Convert a chunk of raw CSV rows into a typed Polars DataFrame.

    Returns a DataFrame with the canonical schema defined in §2.2.
    """
    records: list[dict[str, Any]] = []
    for row in rows:
        if len(row) < 13:
            continue

        post_id = _safe_int(row[IDX_NUM])
        if post_id is None:
            continue

        ts_raw = _safe_int(row[IDX_TIMESTAMP])
        if ts_raw is None:
            continue

        ts_utc = datetime.fromtimestamp(ts_raw, tz=UTC)

        raw_comment = _safe_str(row[IDX_COMMENT]) or ""
        body = _strip_html(raw_comment)
        body_clean = _clean_body(body) if body else ""
        replies = _extract_replies(raw_comment)

        has_image = bool(_safe_str(row[IDX_MEDIA_ORIG]) if len(row) > IDX_MEDIA_ORIG else None)

        records.append(
            {
                "post_id": post_id,
                "thread_id": _safe_int(row[IDX_THREAD]),
                "board": "pol",
                "timestamp_utc": ts_utc,
                "poster_id": _safe_str(row[IDX_POSTER_HASH]),
                "title": _safe_str(row[IDX_TITLE]),
                "body": body,
                "body_clean": body_clean,
                "reply_to": replies,
                "has_image": has_image,
                "country_code": _safe_str(row[IDX_COUNTRY]),
            }
        )

    if not records:
        return pl.DataFrame()

    df = pl.DataFrame(records)
    # Ensure datetime type
    df = df.with_columns(
        pl.col("timestamp_utc").cast(pl.Datetime("us", "UTC")),
    )
    # Add year/month partition columns
    df = df.with_columns(
        pl.col("timestamp_utc").dt.year().alias("year"),
        pl.col("timestamp_utc").dt.month().alias("month"),
    )
    return df


def ingest_pol(
    cfg: Settings,
    *,
    limit: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Phase 1 main: stream-ingest /pol/ tar.gz → partitioned Parquet.

    Parameters
    ----------
    cfg:
        Pipeline settings.
    limit:
        If set, stop after *limit* total rows (for smoke testing).
    dry_run:
        If True, parse but do not write files.

    Returns
    -------
    dict:
        Manifest with per-month stats.
    """
    tar_path = cfg.pol_tar
    out_dir = cfg.pol_parquet

    logger.info("Starting /pol/ ingest: {} → {}", tar_path, out_dir)

    manifest: dict[str, Any] = {"months": {}, "total_rows": 0, "file_hashes": {}}
    all_dfs: list[pl.DataFrame] = []
    total_rows = 0

    for chunk_rows in iter_tar_csv_chunks(tar_path, chunk_size=cfg.ingest_chunk_size):
        df = parse_chunk(chunk_rows)
        if df.height == 0:
            continue

        all_dfs.append(df)
        total_rows += df.height

        if limit and total_rows >= limit:
            logger.info("Hit row limit ({}), stopping", limit)
            break

    if not all_dfs:
        logger.warning("No data parsed from {}", tar_path)
        return manifest

    full_df = pl.concat(all_dfs)
    logger.info("Parsed {} total rows", full_df.height)

    # Compute per-month stats for manifest
    month_stats = (
        full_df.group_by(["year", "month"])
        .agg(
            pl.len().alias("post_count"),
            pl.col("thread_id").n_unique().alias("unique_threads"),
            pl.col("body").str.len_bytes().mean().alias("mean_post_length_bytes"),
            pl.col("body").str.len_bytes().median().alias("median_post_length_bytes"),
        )
        .sort(["year", "month"])
    )

    for row in month_stats.iter_rows(named=True):
        key = f"{row['year']:04d}-{row['month']:02d}"
        manifest["months"][key] = {
            "post_count": row["post_count"],
            "unique_threads": row["unique_threads"],
            "mean_post_length_bytes": round(row["mean_post_length_bytes"] or 0, 1),
            "median_post_length_bytes": round(row["median_post_length_bytes"] or 0, 1),
        }

    manifest["total_rows"] = full_df.height

    if not dry_run:
        # Write partitioned Parquet
        write_partitioned(
            full_df,
            out_dir,
            partition_cols=["year", "month"],
        )

        # Hash output files
        for pq in sorted(out_dir.rglob("*.parquet")):
            rel = str(pq.relative_to(out_dir))
            h = hashlib.sha256()
            with open(pq, "rb") as f:
                for block in iter(lambda: f.read(1 << 20), b""):
                    h.update(block)
            manifest["file_hashes"][rel] = h.hexdigest()

        # Write manifest
        manifest_path = cfg.resolve(cfg.data_interim) / "pol_manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
        logger.info("Manifest written → {}", manifest_path)

    return manifest
