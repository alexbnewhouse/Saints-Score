"""Shared pytest fixtures for the Saints Score test suite."""

from __future__ import annotations

from datetime import UTC
from pathlib import Path

import polars as pl
import pytest

from saints_score.config import Settings


@pytest.fixture
def cfg(tmp_path: Path) -> Settings:
    """Produce a Settings instance pointing at temp dirs."""
    return Settings(
        project_root=tmp_path,
        data_raw=Path("data/raw"),
        data_interim=Path("data/interim"),
        data_processed=Path("data/processed"),
        out_dir=Path("out"),
        run_log_dir=Path("out/runs"),
        pol_tar_path=Path("data/pol/pol.csv.tar.gz"),
        pol_parquet_dir=Path("data/interim/pol"),
        seed=42,
    )


@pytest.fixture
def sample_cases() -> pl.DataFrame:
    """Tiny cases DataFrame for testing."""
    return pl.DataFrame(
        {
            "case_id": ["NZ-2019-TARRANT", "USA-2019-CRUSIUS", "USA-2017-PADDOCK"],
            "perpetrator_name": ["Brenton Tarrant", "Patrick Crusius", "Stephen Paddock"],
            "perp_name": ["Brenton Tarrant", "Patrick Crusius", "Stephen Paddock"],
            "event_date": ["2019-03-15", "2019-08-03", "2017-10-01"],
            "event_year": [2019, 2019, 2017],
            "country": ["NZ", "USA", "USA"],
            "status": ["C", "C", "C"],
            "method_primary": ["firearm", "firearm", "firearm"],
            "fatalities_excl_perp": [51, 23, 60],
            "venue_type": ["religious_site", "retail", "entertainment"],
            "manifesto_exists": ["Y", "Y", "N"],
            "livestream_successful": ["Y", "N", "N"],
            "saints_relevance": ["very_high", "high", "low"],
            "saints_tradition": ["core_farright", "core_farright", "none"],
            "perp_aliases": ["BT;the saint;kebab remover", "crusius", None],
            "perp_age": [28, 21, 64],
            "primary_online_handles": [None, None, None],
        }
    )


@pytest.fixture
def sample_posts() -> pl.DataFrame:
    """Tiny posts DataFrame for testing."""
    from datetime import datetime

    return pl.DataFrame(
        {
            "post_id": [1, 2, 3, 4, 5],
            "thread_id": [100, 100, 200, 200, 300],
            "board": ["pol"] * 5,
            "timestamp_utc": [
                datetime(2019, 3, 15, 12, 0, tzinfo=UTC),
                datetime(2019, 3, 15, 13, 0, tzinfo=UTC),
                datetime(2019, 3, 16, 10, 0, tzinfo=UTC),
                datetime(2019, 8, 3, 15, 0, tzinfo=UTC),
                datetime(2017, 10, 2, 8, 0, tzinfo=UTC),
            ],
            "poster_id": ["abc", "def", "ghi", "jkl", "mno"],
            "title": [None, None, None, None, None],
            "body": [
                "Tarrant was a saint, subscribe to PewDiePie",
                "Horrible tragedy in NZ, RIP to the victims",
                "The kebab remover did nothing wrong",
                "Crusius manifesto was interesting reading",
                "What happened in Vegas was crazy",
            ],
            "body_clean": [
                "tarrant was a saint, subscribe to pewdiepie",
                "horrible tragedy in nz, rip to the victims",
                "the kebab remover did nothing wrong",
                "crusius manifesto was interesting reading",
                "what happened in vegas was crazy",
            ],
            "reply_to": [[], [1], [], [], []],
            "has_image": [False, True, False, False, True],
            "country_code": ["US", "AU", "US", "US", "US"],
        }
    )
