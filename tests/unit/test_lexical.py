"""Tests for saints_score.mentions.lexical — lexical candidate retrieval."""

import polars as pl

from saints_score.mentions.lexical import _tokenize, lexical_candidate_retrieval


def test_tokenize():
    assert _tokenize("Hello World") == ["hello", "world"]
    assert _tokenize("one-two three_four") == ["one", "two", "three_four"]
    assert _tokenize("") == []


def test_lexical_retrieval_exact_match(
    sample_cases: pl.DataFrame, sample_posts: pl.DataFrame, cfg
):
    """Exact substring matching should find attacker names in posts."""
    from saints_score.mentions.aliases import build_seed_aliases

    aliases = build_seed_aliases(sample_cases)
    posts_lf = sample_posts.lazy()

    candidates = lexical_candidate_retrieval(posts_lf, aliases, cfg)
    assert candidates.height > 0
    assert set(candidates.columns) == {
        "post_id",
        "attacker_id",
        "alias_matched",
        "match_type",
        "score",
    }

    # "tarrant" should match posts 1 and 3 (via "tarrant" and "kebab remover")
    tarrant_matches = candidates.filter(pl.col("attacker_id") == "NZ-2019-TARRANT")
    assert tarrant_matches.height >= 1

    # Crusius should match post 4
    crusius_matches = candidates.filter(pl.col("attacker_id") == "USA-2019-CRUSIUS")
    assert crusius_matches.height >= 1


def test_lexical_retrieval_empty_aliases(sample_posts: pl.DataFrame, cfg):
    """Empty alias list should return empty DataFrame with correct schema."""
    aliases = pl.DataFrame(schema={"attacker_id": pl.Utf8, "alias": pl.Utf8, "source": pl.Utf8})
    posts_lf = sample_posts.lazy()
    candidates = lexical_candidate_retrieval(posts_lf, aliases, cfg)
    assert candidates.height == 0
    assert "post_id" in candidates.columns


def test_lexical_retrieval_short_aliases_filtered(sample_posts: pl.DataFrame, cfg):
    """Aliases shorter than min_alias_token_len should be filtered out."""
    aliases = pl.DataFrame(
        {
            "attacker_id": ["TEST-001"],
            "alias": ["ab"],  # too short (< 4 chars)
            "source": ["test"],
        }
    )
    posts_lf = sample_posts.lazy()
    candidates = lexical_candidate_retrieval(posts_lf, aliases, cfg)
    assert candidates.height == 0
