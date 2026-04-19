"""Parquet I/O helpers — read/write with zstd compression, partitioned writes."""

from __future__ import annotations

from typing import TYPE_CHECKING

import polars as pl

from saints_score.logging import logger

if TYPE_CHECKING:
    from pathlib import Path

# Default compression for all pipeline Parquet output.
COMPRESSION = "zstd"


def write_parquet(df: pl.DataFrame, path: Path, *, compression: str = COMPRESSION) -> Path:
    """Write a DataFrame to Parquet with zstd compression.  Creates parent dirs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(path, compression=compression)
    logger.debug("Wrote {} rows → {}", df.height, path)
    return path


def read_parquet(path: Path, *, columns: list[str] | None = None) -> pl.DataFrame:
    """Read a Parquet file (optionally selecting columns)."""
    return pl.read_parquet(path, columns=columns)


def scan_parquet(path: Path | str, *, columns: list[str] | None = None) -> pl.LazyFrame:
    """Lazy-scan a Parquet file or glob pattern."""
    lf = pl.scan_parquet(path)
    if columns:
        lf = lf.select(columns)
    return lf


def write_partitioned(
    df: pl.DataFrame,
    base_dir: Path,
    partition_cols: list[str],
    *,
    compression: str = COMPRESSION,
) -> int:
    """Write a DataFrame as Hive-partitioned Parquet.

    Returns the number of partition files written.
    """
    base_dir.mkdir(parents=True, exist_ok=True)
    groups = df.partition_by(partition_cols, as_dict=True)
    n_written = 0
    for keys, part_df in groups.items():
        if not isinstance(keys, tuple):
            keys = (keys,)
        parts = "/".join(f"{col}={val}" for col, val in zip(partition_cols, keys, strict=True))
        out_path = base_dir / parts / "part-0.parquet"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        part_df.drop(partition_cols).write_parquet(out_path, compression=compression)
        n_written += 1
    logger.info("Wrote {} partitions → {}", n_written, base_dir)
    return n_written


def scan_partitioned(base_dir: Path) -> pl.LazyFrame:
    """Lazy-scan a Hive-partitioned Parquet directory."""
    return pl.scan_parquet(
        str(base_dir / "**/*.parquet"),
        hive_partitioning=True,
    )
