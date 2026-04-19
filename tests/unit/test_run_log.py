"""Tests for saints_score.io.run_log — run logging utilities."""

from pathlib import Path

from saints_score.io.run_log import RunLog


def test_run_log_save(tmp_path: Path):
    log = RunLog(phase="test", config={"seed": 42})
    log.metrics = {"n_rows": 100}

    # Create a dummy input file to hash
    dummy = tmp_path / "input.txt"
    dummy.write_text("test data")
    log.hash_input(dummy)

    out = log.save(tmp_path / "runs")
    assert out.exists()
    assert (out / "config.json").exists()
    assert (out / "inputs.sha256").exists()
    assert (out / "duration.json").exists()
    assert (out / "metrics.json").exists()
