#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["polars>=1.0"]
# ///
"""Audit every column in cases.csv against the schema rules."""
from __future__ import annotations
import polars as pl
from collections import Counter

df = pl.read_csv("out/cases.csv", infer_schema_length=0)  # all strings for raw inspection
print(f"Shape: {df.shape}\n")

# ── field type manifests (from spec) ──
INT_FIELDS = {
    "event_year", "perp_age", "fatalities_total_incl_perp",
    "fatalities_excl_perp", "total_casualties",
    "incoming_citation_count", "outgoing_citation_count",
    "manifesto_length_pages", "livestream_duration_min",
}

ENUM_FIELDS = {
    "status": {"C", "PF", "F"},
    "perp_sex": {"M", "F", "trans_MtF", "trans_FtM", "mixed"},
    "perp_died": {"Y", "N"},
    "perp_mental_health_flag": {"Y", "N", "Contested"},
    "method_primary": {"firearm", "vehicle", "blade", "arson", "explosive", "mixed", "other"},
    "manifesto_exists": {"Y", "N", "Partial"},
    "livestream_attempted": {"Y", "N"},
    "livestream_successful": {"Y", "N", "Partial"},
    "ideology_contested": {"Y", "N"},
    "gamification_elements": {"Y", "N"},
    "first_person_camera": {"Y", "N"},
    "anniversary_attack": {"Y", "N"},
    "prior_warning_signs": {"Y", "N"},
    "saints_relevance": {"low", "medium", "medium_high", "high", "very_high", "contested"},
    "saints_tradition": {
        "core_farright", "incel", "kolumbayn", "columbine_fandom",
        "tcc", "jihadist", "mixed", "none", "misc",
    },
    "saints_canon_validation_corpus": {"Y", "N"},
    "evidence_tier": {"1", "2", "3"},
    "venue_type": {
        "religious_site", "school", "university", "entertainment", "retail",
        "transit", "public_space", "residence", "government", "workplace",
        "healthcare", "rural", "multi_site", "other", "political", "political_rally",
    },
    "target_type": {
        "religious", "ethnic", "lgbtq", "women", "political", "school_random",
        "university_random", "random_public", "workplace", "family", "police",
        "disabled_persons", "community", "mixed", "other",
    },
}

LIST_FIELDS = {
    "subculture_tags", "primary_online_handles", "primary_platforms",
    "named_prior_attackers_incoming", "named_by_subsequent_attackers",
    "cross_references", "key_sources",
}

REQUIRED_FIELDS = {"case_id", "event_date", "event_year", "country", "status"}

# ── Audit ──
issues: list[str] = []

for col in df.columns:
    series = df[col]
    n_null = series.null_count()
    n_empty = (series == "").sum()
    n_total = series.len()
    n_filled = n_total - n_null - n_empty

    print(f"━━━ {col} ━━━  ({n_filled} filled, {n_null} null, {n_empty} empty)")

    non_null = series.drop_nulls().filter(series.drop_nulls() != "")

    if col in REQUIRED_FIELDS and (n_null > 0 or n_empty > 0):
        missing_ids = df.filter(series.is_null() | (series == ""))["case_id"].to_list()
        issues.append(f"REQUIRED MISSING: {col} missing in {len(missing_ids)} rows: {missing_ids[:10]}")

    if col in INT_FIELDS:
        # Check all values are parseable as integers
        bad = []
        for val in non_null.to_list():
            try:
                int(val)
            except (ValueError, TypeError):
                bad.append(val)
        if bad:
            issues.append(f"INT_PARSE: {col} has {len(bad)} non-integer values: {bad[:10]}")
            print(f"  ⚠ Non-integer values: {Counter(bad).most_common(10)}")

    elif col in ENUM_FIELDS:
        domain = ENUM_FIELDS[col]
        vals = non_null.unique().to_list()
        bad = [v for v in vals if v not in domain]
        if bad:
            issues.append(f"ENUM_MISMATCH: {col} has {len(bad)} out-of-domain values: {bad}")
            print(f"  ⚠ Out-of-domain ({len(bad)}):")
            for b in sorted(bad):
                cnt = (series == b).sum()
                print(f"    {cnt}× \"{b}\"")
        good = [v for v in vals if v in domain]
        print(f"  ✓ In-domain: {sorted(good)}")

    elif col == "event_date":
        import re
        bad_dates = []
        for val in non_null.to_list():
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", val):
                bad_dates.append(val)
        if bad_dates:
            issues.append(f"DATE_FORMAT: {col} has {len(bad_dates)} non-ISO values: {bad_dates[:10]}")
            print(f"  ⚠ Non-ISO dates: {bad_dates[:10]}")

    elif col in LIST_FIELDS:
        # Check semicolons are used as separators
        has_semi = (non_null.str.contains(";")).sum()
        print(f"  Semicolon-delimited: {has_semi}/{non_null.len()} rows")

    else:
        # Free-text: just show value-length stats + unique count
        if non_null.len() > 0:
            lengths = non_null.str.len_chars()
            print(f"  Value lengths: min={lengths.min()}, max={lengths.max()}, median={lengths.median()}")
            print(f"  Unique values: {non_null.n_unique()}")
        # Show distribution for low-cardinality cols
        if non_null.n_unique() <= 20 and non_null.len() > 0:
            vc = Counter(non_null.to_list())
            for v, c in vc.most_common():
                print(f"    {c}× \"{v}\"")

    print()

# ── Consistency checks ──
print("\n━━━ CROSS-FIELD CONSISTENCY ━━━\n")

df_typed = pl.read_csv("out/cases.csv")

# fatalities: total_incl_perp >= excl_perp
if "fatalities_total_incl_perp" in df_typed.columns and "fatalities_excl_perp" in df_typed.columns:
    both = df_typed.filter(
        pl.col("fatalities_total_incl_perp").is_not_null() &
        pl.col("fatalities_excl_perp").is_not_null()
    )
    bad = both.filter(pl.col("fatalities_total_incl_perp") < pl.col("fatalities_excl_perp"))
    if bad.height > 0:
        issues.append(f"CONSISTENCY: {bad.height} rows where fatalities_total_incl_perp < fatalities_excl_perp")
        print(f"⚠ fatalities_total < fatalities_excl in {bad.height} rows:")
        for row in bad.select("case_id", "fatalities_total_incl_perp", "fatalities_excl_perp").iter_rows(named=True):
            print(f"  {row}")

# perp_died=Y → fatalities_total should be fatalities_excl + 1 (or more if multiple perps)
if "perp_died" in df_typed.columns:
    died = df_typed.filter(
        (pl.col("perp_died") == "Y") &
        pl.col("fatalities_total_incl_perp").is_not_null() &
        pl.col("fatalities_excl_perp").is_not_null()
    )
    bad_died = died.filter(pl.col("fatalities_total_incl_perp") <= pl.col("fatalities_excl_perp"))
    if bad_died.height > 0:
        issues.append(f"CONSISTENCY: {bad_died.height} rows where perp_died=Y but total_incl_perp ≤ excl_perp")
        print(f"\n⚠ perp_died=Y but total_incl ≤ excl in {bad_died.height} rows:")
        for row in bad_died.select("case_id", "fatalities_total_incl_perp", "fatalities_excl_perp").iter_rows(named=True):
            print(f"  {row}")

# perp_died=N → fatalities_total should equal fatalities_excl
if "perp_died" in df_typed.columns:
    alive = df_typed.filter(
        (pl.col("perp_died") == "N") &
        pl.col("fatalities_total_incl_perp").is_not_null() &
        pl.col("fatalities_excl_perp").is_not_null()
    )
    bad_alive = alive.filter(pl.col("fatalities_total_incl_perp") != pl.col("fatalities_excl_perp"))
    if bad_alive.height > 0:
        issues.append(f"CONSISTENCY: {bad_alive.height} rows where perp_died=N but total_incl ≠ excl")
        print(f"\n⚠ perp_died=N but total_incl ≠ excl in {bad_alive.height} rows:")
        for row in bad_alive.select("case_id", "fatalities_total_incl_perp", "fatalities_excl_perp").iter_rows(named=True):
            print(f"  {row}")

# total_casualties should be >= fatalities_excl_perp
if "total_casualties" in df_typed.columns and "fatalities_excl_perp" in df_typed.columns:
    both2 = df_typed.filter(
        pl.col("total_casualties").is_not_null() &
        pl.col("fatalities_excl_perp").is_not_null()
    )
    bad2 = both2.filter(pl.col("total_casualties") < pl.col("fatalities_excl_perp"))
    if bad2.height > 0:
        issues.append(f"CONSISTENCY: {bad2.height} rows where total_casualties < fatalities_excl_perp")
        print(f"\n⚠ total_casualties < fatalities_excl in {bad2.height} rows:")
        for row in bad2.select("case_id", "total_casualties", "fatalities_excl_perp").iter_rows(named=True):
            print(f"  {row}")

# event_year should match event_date year
if "event_year" in df_typed.columns and "event_date" in df_typed.columns:
    has_both = df_typed.filter(
        pl.col("event_year").is_not_null() &
        pl.col("event_date").is_not_null()
    )
    bad_yr = has_both.filter(pl.col("event_year") != pl.col("event_date").dt.year())
    if bad_yr.height > 0:
        issues.append(f"CONSISTENCY: {bad_yr.height} rows where event_year ≠ event_date.year")
        print(f"\n⚠ event_year ≠ date year in {bad_yr.height} rows:")
        for row in bad_yr.select("case_id", "event_year", "event_date").iter_rows(named=True):
            print(f"  {row}")

# status=F → fatalities should be 0
if "status" in df_typed.columns and "fatalities_excl_perp" in df_typed.columns:
    foiled = df_typed.filter(
        (pl.col("status") == "F") &
        pl.col("fatalities_excl_perp").is_not_null()
    )
    bad_foiled = foiled.filter(pl.col("fatalities_excl_perp") > 0)
    if bad_foiled.height > 0:
        issues.append(f"CONSISTENCY: {bad_foiled.height} foiled plots (status=F) with fatalities_excl_perp > 0")
        print(f"\n⚠ Foiled but fatalities > 0 in {bad_foiled.height} rows:")
        for row in bad_foiled.select("case_id", "fatalities_excl_perp").iter_rows(named=True):
            print(f"  {row}")

# manifesto_exists=N → manifesto_title/length/format/language/platform should be null
if "manifesto_exists" in df_typed.columns:
    no_man = df_typed.filter(pl.col("manifesto_exists") == "N")
    man_fields = ["manifesto_title", "manifesto_length_pages", "manifesto_format", "manifesto_language", "manifesto_platform"]
    for mf in man_fields:
        if mf in df_typed.columns:
            bad_mf = no_man.filter(pl.col(mf).is_not_null())
            if bad_mf.height > 0:
                issues.append(f"CONSISTENCY: {bad_mf.height} rows where manifesto_exists=N but {mf} is not null")
                print(f"\n⚠ manifesto_exists=N but {mf} filled in {bad_mf.height} rows:")
                for row in bad_mf.select("case_id", mf).iter_rows(named=True):
                    print(f"  {row}")

# livestream_attempted=N → livestream_successful/platform/duration should be null
if "livestream_attempted" in df_typed.columns:
    # Need to handle annotated values like "N (passively livestreamed...)"
    pass  # This has annotated values, skip strict check

# ── Summary ──
print(f"\n━━━ ISSUE SUMMARY ({len(issues)} issues) ━━━\n")
for i, issue in enumerate(issues, 1):
    print(f"  {i}. {issue}")
