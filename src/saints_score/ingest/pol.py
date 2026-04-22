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

from saints_score.io.tar_stream import iter_tar_csv_chunks
from saints_score.logging import logger

if TYPE_CHECKING:
    from saints_score.config import Settings

# ── 4plebs CSV column mapping ──────────────────────────────────────────────
# Actual column order in the 4plebs /pol/ CSV dump (28 columns, NO header row):
#  0 num              1 subnum           2 thread_num       3 op
#  4 timestamp         5 fourchan_date    6 media_filename   7 media_w
#  8 media_h           9 preview_orig    10 preview_w       11 preview_h
# 12 media_size       13 media_hash      14 media_orig      15 spoiler
# 16 deleted          17 capcode         18 email           19 name
# 20 trip             21 title           22 comment         23 sticky
# 24 locked           25 poster_hash     26 poster_country  27 exif

# Indices we actually need
IDX_NUM = 0
IDX_THREAD = 2
IDX_TIMESTAMP = 4
IDX_TITLE = 21
IDX_COMMENT = 22
IDX_POSTER_HASH = 25
IDX_COUNTRY = 26
IDX_MEDIA_ORIG = 14

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
    out: list[int] = []
    for m in _REPLY_RE.findall(text):
        v = int(m)
        if v <= _I64_MAX:
            out.append(v)
    return out


_I64_MAX = (1 << 63) - 1


def _safe_int(val: str) -> int | None:
    """Parse a string to int, returning None for \\N, empty, or overflow."""
    if not val or val == "\\N" or val == "N":
        return None
    try:
        v = int(val)
    except ValueError:
        return None
    if v < 0 or v > _I64_MAX:
        return None
    return v


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
        if len(row) < 23:
            continue

        post_id = _safe_int(row[IDX_NUM])
        if post_id is None:
            continue

        ts_raw = _safe_int(row[IDX_TIMESTAMP])
        if ts_raw is None:
            continue

        ts_utc = datetime.fromtimestamp(ts_raw, tz=UTC)

        # Filter out corrupted timestamps outside the 4plebs /pol/ archive range
        if ts_utc.year < 2013 or ts_utc.year > 2025:
            continue

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
                "poster_id": _safe_str(row[IDX_POSTER_HASH]) if len(row) > IDX_POSTER_HASH else None,
                "title": _safe_str(row[IDX_TITLE]),
                "body": body,
                "body_clean": body_clean,
                "reply_to": replies,
                "has_image": has_image,
                "country_code": _safe_str(row[IDX_COUNTRY]) if len(row) > IDX_COUNTRY else None,
            }
        )

    if not records:
        return pl.DataFrame()

    df = pl.DataFrame(
        records,
        schema={
            "post_id": pl.Int64,
            "thread_id": pl.Int64,
            "board": pl.Utf8,
            "timestamp_utc": pl.Datetime("us", "UTC"),
            "poster_id": pl.Utf8,
            "title": pl.Utf8,
            "body": pl.Utf8,
            "body_clean": pl.Utf8,
            "reply_to": pl.List(pl.Int64),
            "has_image": pl.Boolean,
            "country_code": pl.Utf8,
        },
    )
    # Add year/month partition columns
    df = df.with_columns(
        pl.col("timestamp_utc").dt.year().alias("year"),
        pl.col("timestamp_utc").dt.month().alias("month"),
    )
    return df


def _append_partitioned(
    df: pl.DataFrame,
    base_dir: Any,
    partition_cols: list[str],
    part_counters: dict[str, int],
) -> None:
    """Append a chunk to Hive-partitioned Parquet, creating new part files."""
    groups = df.partition_by(partition_cols, as_dict=True)
    for keys, part_df in groups.items():
        if not isinstance(keys, tuple):
            keys = (keys,)
        parts = "/".join(f"{col}={val}" for col, val in zip(partition_cols, keys, strict=True))
        idx = part_counters.get(parts, 0)
        out_path = base_dir / parts / f"part-{idx}.parquet"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        part_df.drop(partition_cols).write_parquet(out_path, compression="zstd")
        part_counters[parts] = idx + 1


def ingest_pol(
    cfg: Settings,
    *,
    limit: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Phase 1 main: stream-ingest /pol/ tar.gz → partitioned Parquet.

    Writes partitioned Parquet **incrementally** (chunk-by-chunk) to keep peak
    memory at ~1 chunk instead of the full corpus.

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
    # Accumulate lightweight per-month stats without keeping row data
    month_post_count: dict[str, int] = {}
    month_unique_threads: dict[str, set[int]] = {}
    month_body_lens: dict[str, list[float]] = {}
    part_counters: dict[str, int] = {}
    total_rows = 0

    out_dir.mkdir(parents=True, exist_ok=True)

    for chunk_rows in iter_tar_csv_chunks(tar_path, chunk_size=cfg.ingest_chunk_size):
        df = parse_chunk(chunk_rows)
        if df.height == 0:
            continue

        total_rows += df.height

        # Write this chunk's partitions immediately (no accumulation)
        if not dry_run:
            _append_partitioned(df, out_dir, ["year", "month"], part_counters)

        # Accumulate lightweight stats per (year, month)
        stats = (
            df.group_by(["year", "month"])
            .agg(
                pl.len().alias("post_count"),
                pl.col("thread_id").alias("_threads"),
                pl.col("body").str.len_bytes().mean().alias("mean_len"),
            )
        )
        for row in stats.iter_rows(named=True):
            key = f"{row['year']:04d}-{row['month']:02d}"
            month_post_count[key] = month_post_count.get(key, 0) + row["post_count"]
            if key not in month_unique_threads:
                month_unique_threads[key] = set()
            month_unique_threads[key].update(t for t in row["_threads"] if t is not None)
            # Running mean approximation: store weighted mean
            if key not in month_body_lens:
                month_body_lens[key] = [0.0, 0]  # type: ignore[assignment]
            prev_sum, prev_n = month_body_lens[key]  # type: ignore[misc]
            cur_mean = row["mean_len"] or 0.0
            month_body_lens[key] = [prev_sum + cur_mean * row["post_count"], prev_n + row["post_count"]]  # type: ignore[assignment]

        if limit and total_rows >= limit:
            logger.info("Hit row limit ({}), stopping", limit)
            break

    logger.info("Parsed {} total rows", total_rows)

    if total_rows == 0:
        logger.warning("No data parsed from {}", tar_path)
        return manifest

    # Build manifest from accumulated stats
    for key in sorted(month_post_count):
        weighted_sum, n = month_body_lens.get(key, [0.0, 0])  # type: ignore[misc]
        manifest["months"][key] = {
            "post_count": month_post_count[key],
            "unique_threads": len(month_unique_threads.get(key, set())),
            "mean_post_length_bytes": round(weighted_sum / max(n, 1), 1),
        }

    manifest["total_rows"] = total_rows

    if not dry_run:
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
