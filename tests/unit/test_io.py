"""Tests for saints_score.io.parquet — read/write helpers."""

from pathlib import Path

import polars as pl

from saints_score.io.parquet import read_parquet, write_parquet, write_partitioned


def test_write_read_roundtrip(tmp_path: Path):
    df = pl.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    path = tmp_path / "test.parquet"
    write_parquet(df, path)
    result = read_parquet(path)
    assert result.equals(df)


def test_write_partitioned(tmp_path: Path):
    df = pl.DataFrame({
        "year": [2019, 2019, 2020],
        "month": [3, 4, 1],
        "value": [10, 20, 30],
    })
    n = write_partitioned(df, tmp_path / "partitioned", ["year", "month"])
    assert n == 3

    # Check directory structure
    assert (tmp_path / "partitioned" / "year=2019" / "month=3" / "part-0.parquet").exists()
    assert (tmp_path / "partitioned" / "year=2020" / "month=1" / "part-0.parquet").exists()
