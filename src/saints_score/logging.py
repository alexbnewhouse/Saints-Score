"""Structured logging with loguru.

Provides a pre-configured ``logger`` and a ``setup_logging`` helper that scripts
call at startup to route logs to stderr + an optional file.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from loguru import logger as _logger

if TYPE_CHECKING:
    from pathlib import Path

# Re-export the singleton so callers do ``from saints_score.logging import logger``
logger = _logger


def setup_logging(
    *,
    level: str = "INFO",
    log_file: Path | None = None,
    serialize: bool = False,
) -> None:
    """Configure loguru for a pipeline run.

    Parameters
    ----------
    level:
        Minimum log level for stderr output.
    log_file:
        If given, also write logs (DEBUG level) to this file.
    serialize:
        If *True*, file logs are JSON-serialised (for machine parsing).
    """
    _logger.remove()  # clear default handler

    _logger.add(
        sys.stderr,
        level=level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        _logger.add(
            str(log_file),
            level="DEBUG",
            serialize=serialize,
            rotation="50 MB",
            retention=5,
            encoding="utf-8",
        )
