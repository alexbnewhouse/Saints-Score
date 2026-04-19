"""Tests for saints_score.mentions.aliases — seed alias building."""

import polars as pl

from saints_score.mentions.aliases import build_seed_aliases


def test_build_seed_aliases(sample_cases: pl.DataFrame):
    aliases = build_seed_aliases(sample_cases)
    assert aliases.height > 0
    assert "attacker_id" in aliases.columns
    assert "alias" in aliases.columns
    assert "source" in aliases.columns

    # Tarrant should have canonical + last name + aliases
    tarrant = aliases.filter(pl.col("attacker_id") == "NZ-2019-TARRANT")
    assert tarrant.height >= 3  # canonical, last name, plus aliases

    # Paddock has no aliases field
    paddock = aliases.filter(pl.col("attacker_id") == "USA-2017-PADDOCK")
    assert paddock.height >= 2  # canonical + last name


def test_build_seed_aliases_empty():
    df = pl.DataFrame(
        {
            "case_id": ["TEST-001"],
            "perpetrator_name": [None],
        }
    )
    aliases = build_seed_aliases(df)
    assert aliases.height == 0
