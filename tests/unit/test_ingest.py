"""Tests for saints_score.ingest.pol — parsing and normalisation."""

from saints_score.ingest.pol import (
    _clean_body,
    _extract_replies,
    _strip_html,
    parse_chunk,
)


def test_strip_html():
    result = _strip_html("<b>hello</b> &amp; world")
    # Tag stripping may leave extra whitespace; normalise for comparison
    assert " ".join(result.split()) == "hello & world"
    assert _strip_html("no tags") == "no tags"
    assert _strip_html("") == ""


def test_clean_body():
    result = _clean_body(">implying\nSome \t TEXT  here")
    assert result == "implying some text here"


def test_extract_replies():
    assert _extract_replies(">>12345 some text >>67890") == [12345, 67890]
    assert _extract_replies("no replies here") == []


def test_parse_chunk_with_valid_rows():
    # Row must be at least 27 columns long; column indices match pol.py constants:
    # IDX_NUM=0, IDX_THREAD=2, IDX_TIMESTAMP=4, IDX_MEDIA_ORIG=14,
    # IDX_TITLE=21, IDX_COMMENT=22, IDX_POSTER_HASH=25, IDX_COUNTRY=26
    row = [""] * 27
    row[0] = "1001"        # post_id
    row[2] = "1000"        # thread_id
    row[4] = "1553000000"  # timestamp
    row[14] = "img.jpg"    # media_orig (has_image)
    row[21] = "Test Title" # title
    row[22] = "Hello <b>world</b>"  # body (comment)
    row[25] = "poster1"    # poster_hash
    row[26] = "US"         # country
    rows = [row]
    df = parse_chunk(rows)
    assert df.height == 1
    assert df["post_id"][0] == 1001
    assert df["thread_id"][0] == 1000
    assert "world" in df["body"][0]
    assert df["board"][0] == "pol"


def test_parse_chunk_skips_short_rows():
    rows = [["too", "short"]]
    df = parse_chunk(rows)
    assert df.height == 0
