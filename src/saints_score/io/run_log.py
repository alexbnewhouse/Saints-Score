"""Run-logging utilities — structured logging of pipeline phase executions."""

from __future__ import annotations

import hashlib
import json
import subprocess
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from saints_score.logging import logger

if TYPE_CHECKING:
    from pathlib import Path


def _sha256(path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_sha() -> str | None:
    """Return the current git HEAD SHA, or None if not in a repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


@dataclass
class RunLog:
    """Accumulates metadata for a single pipeline phase execution."""

    phase: str
    config: dict[str, Any] = field(default_factory=dict)
    input_hashes: dict[str, str] = field(default_factory=dict)
    output_hashes: dict[str, str] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    _start: float = field(default_factory=time.monotonic, init=False, repr=False)

    def hash_input(self, path: Path) -> None:
        """Record SHA-256 of an input file."""
        self.input_hashes[str(path)] = _sha256(path)

    def hash_output(self, path: Path) -> None:
        """Record SHA-256 of an output file."""
        self.output_hashes[str(path)] = _sha256(path)

    def save(self, run_dir: Path) -> Path:
        """Persist the run log to ``run_dir``."""
        ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        out = run_dir / f"{ts}_{self.phase}"
        out.mkdir(parents=True, exist_ok=True)

        elapsed = time.monotonic() - self._start

        (out / "config.json").write_text(
            json.dumps(self.config, indent=2, default=str), encoding="utf-8"
        )
        (out / "inputs.sha256").write_text(
            json.dumps(self.input_hashes, indent=2), encoding="utf-8"
        )
        (out / "outputs.sha256").write_text(
            json.dumps(self.output_hashes, indent=2), encoding="utf-8"
        )
        (out / "duration.json").write_text(
            json.dumps({"elapsed_seconds": round(elapsed, 2)}), encoding="utf-8"
        )

        git = _git_sha()
        if git:
            (out / "git_sha").write_text(git, encoding="utf-8")

        if self.metrics:
            (out / "metrics.json").write_text(
                json.dumps(self.metrics, indent=2, default=str), encoding="utf-8"
            )

        logger.info("Run log saved → {} ({:.1f}s)", out, elapsed)
        return out
