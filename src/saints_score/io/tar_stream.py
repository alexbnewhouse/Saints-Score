"""Streaming tar.gz reader for the 4plebs /pol/ CSV dump."""

from __future__ import annotations

import csv
import io
import tarfile
from typing import TYPE_CHECKING

from saints_score.logging import logger

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


def iter_tar_csv_chunks(
    tar_path: Path,
    chunk_size: int = 1_000_000,
) -> Iterator[list[list[str]]]:
    """Yield chunks of rows from the first CSV inside a tar.gz archive.

    Each yielded chunk is a list of *chunk_size* rows, where each row is a list
    of string values.  The header row is **not** yielded; it is returned via the
    class interface instead.

    Parameters
    ----------
    tar_path:
        Path to the ``*.csv.tar.gz`` file.
    chunk_size:
        Number of CSV rows per chunk.
    """
    logger.info("Opening tar archive: {}", tar_path)

    with tarfile.open(tar_path, "r:gz") as tf:
        # Grab the first CSV member
        csv_member = None
        for member in tf:
            if member.name.endswith(".csv"):
                csv_member = member
                break
        if csv_member is None:
            raise FileNotFoundError(f"No .csv file found inside {tar_path}")

        logger.info("Streaming CSV member: {} ({:.1f} MB compressed)", csv_member.name, csv_member.size / 1e6)

        fobj = tf.extractfile(csv_member)
        if fobj is None:
            raise FileNotFoundError(f"Cannot extract {csv_member.name}")

        text_stream = io.TextIOWrapper(fobj, encoding="utf-8", errors="replace")
        reader = csv.reader(text_stream)

        # Skip header
        header = next(reader)
        logger.debug("CSV header ({} cols): {}", len(header), header[:5])

        chunk: list[list[str]] = []
        total_rows = 0
        for row in reader:
            chunk.append(row)
            if len(chunk) >= chunk_size:
                total_rows += len(chunk)
                logger.debug("Yielding chunk of {} rows (total so far: {})", len(chunk), total_rows)
                yield chunk
                chunk = []

        if chunk:
            total_rows += len(chunk)
            yield chunk

        logger.info("Finished streaming: {} total rows", total_rows)


def get_tar_csv_header(tar_path: Path) -> list[str]:
    """Read and return just the CSV header from a tar.gz archive."""
    with tarfile.open(tar_path, "r:gz") as tf:
        for member in tf:
            if member.name.endswith(".csv"):
                fobj = tf.extractfile(member)
                if fobj is None:
                    continue
                text_stream = io.TextIOWrapper(fobj, encoding="utf-8", errors="replace")
                reader = csv.reader(text_stream)
                return next(reader)
    raise FileNotFoundError(f"No .csv file found inside {tar_path}")
