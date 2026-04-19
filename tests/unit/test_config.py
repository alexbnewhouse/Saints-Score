"""Tests for saints_score.config."""

from pathlib import Path

from saints_score.config import Settings, get_settings


def test_default_settings():
    """Settings can be instantiated with defaults."""
    s = Settings()
    assert s.seed == 20260414
    assert s.embedding_model == "nomic-ai/nomic-embed-text-v1.5"


def test_resolve_relative(tmp_path: Path):
    """resolve() anchors relative paths to project_root."""
    s = Settings(project_root=tmp_path)
    p = s.resolve(Path("data/raw"))
    assert p == tmp_path / "data" / "raw"


def test_resolve_absolute(tmp_path: Path):
    """resolve() returns absolute paths unchanged."""
    s = Settings(project_root=tmp_path)
    p = s.resolve(Path("/absolute/path"))
    assert p == Path("/absolute/path")


def test_get_settings_no_toml():
    """get_settings() works without a config file."""
    s = get_settings()
    assert isinstance(s, Settings)
