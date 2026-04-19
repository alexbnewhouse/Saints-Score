# Conversion Prompt for Coding Agent

**Purpose**: Convert the batched markdown dataset (files `part01` through `part11`) into normalized CSV/JSON tables for analysis in Polars/pandas.

**Hand this file, plus all part0X .md files, to the coding agent.**

---

## Task

You're given a set of markdown files documenting ~160 mass-violence events in OECD countries 2001–2026. Each case has a `### CASE_ID` header followed by `- field: value` bullets. Your job is to parse all of them into clean, structured tables.

## Input files

- `part01_schema_and_2001-2015.md` — full schema definition + 2001-2015 cases
- `part02_2016-2017.md` — 2016-2017 cases
- `part03_2018-2019.md` — 2018-2019 cases
- `part04_2020-2021.md` — 2020-2021 cases
- `part05_2022.md` — 2022 cases
- `part06_2023.md` — 2023 cases
- `part07_2024.md` — 2024 cases
- `part08_2025-2026.md` — 2025-2026 cases
- `part09_foiled_plots.md` — foiled pre-attack plots (`status: F`)
- `part10_network_analysis.md` — directional citation/influence network edges (different schema — see below)
- `part11_audit_and_gaps.md` — documentation; do NOT ingest as cases

## Tech requirements

- Python ≥ 3.11
- **Polars preferred** over pandas (Alex's default stack)
- Run in a single `uv run` script with inline dependencies OR in a standard venv
- Don't use LLM APIs for parsing. This is purely deterministic markdown-parsing.

## Expected outputs (in `out/`)

```
out/
├── cases.csv              # wide-format, one row per case
├── cases.parquet          # same, as parquet
├── schema.json            # column dtypes + enum domains
├── influences.csv         # long-format citation edges (from part10)
├── platforms.csv          # long-format case×platform
├── subculture_tags.csv    # long-format case×subculture_tag
├── cross_references.csv   # long-format case×source_dataset
├── key_sources.csv        # long-format case×source
├── audit_flags.csv        # list of flagged cases with reason
├── validation_corpus.csv  # validation-corpus cases by tradition (from part11)
└── validation_report.txt  # enum-mismatch + missing-field report
```

## Parsing algorithm

1. **Find case files**: glob `part0[1-9]*.md` and `part1[01-08]*.md` for event cases. `part10` has different schema (network edges). `part11` is documentation — skip for ingest.
2. **Split each file into cases** by splitting on `\n### ` boundary (first one is file header, skip it). The line after `### ` is the `case_id`.
3. **Parse bullets** matching the pattern `^- (\w[\w_]*): (.*)$`. Strip whitespace from values. Empty/missing fields → `None`.
4. **Trim schema header in part01** — the cases start at the first `### ` that looks like a case_id (format: `COUNTRY-YEAR-NAME`, all caps with hyphens). Skip the schema section before cases begin.
5. **Normalize values**:
   - Integer fields (see `INT_FIELDS` below): cast to int; if value is `unknown`/`null`/empty → None.
   - Enum fields: validate against the enum list. Unknown value → keep as string but add to `validation_report.txt`.
   - Semicolon-separated list fields (see `LIST_FIELDS` below): split on `;`, strip each element, drop empties.
   - Boolean-ish Y/N/Contested/Partial: preserve as string (these aren't pure booleans).
   - Verbatim quoted strings (e.g. `weapon_inscriptions`): preserve quotes exactly.

## Field-type manifest

```python
# fields expected to be integers (nullable)
INT_FIELDS = [
    "event_year", "perp_age", "fatalities_total_incl_perp", "fatalities_excl_perp",
    "total_casualties", "incoming_citation_count", "outgoing_citation_count",
    "manifesto_length_pages", "livestream_duration_min",
]

# semicolon-separated list fields → exploded into long-format auxiliary tables
LIST_FIELDS = [
    "subculture_tags",
    "primary_online_handles",
    "primary_platforms",
    "named_prior_attackers_incoming",
    "named_by_subsequent_attackers",
    "cross_references",
    "key_sources",
]

# enum fields → validate (values from part01 schema)
ENUM_FIELDS = {
    "status": ["C", "PF", "F"],
    "perp_sex": ["M", "F", "trans_MtF", "trans_FtM", "mixed"],
    "perp_died": ["Y", "N"],
    "perp_mental_health_flag": ["Y", "N", "Contested"],
    "method_primary": ["firearm", "vehicle", "blade", "arson", "explosive", "mixed", "other"],
    "manifesto_exists": ["Y", "N", "Partial"],
    "livestream_attempted": ["Y", "N"],
    "livestream_successful": ["Y", "N", "Partial"],
    "ideology_contested": ["Y", "N"],
    "gamification_elements": ["Y", "N"],
    "first_person_camera": ["Y", "N"],
    "anniversary_attack": ["Y", "N"],
    "prior_warning_signs": ["Y", "N"],
    "saints_relevance": ["low", "medium", "medium_high", "high", "very_high", "contested"],
    "saints_tradition": [
        "core_farright", "incel", "kolumbayn", "columbine_fandom",
        "tcc", "jihadist", "mixed", "none", "misc"
    ],
    "saints_canon_validation_corpus": ["Y", "N"],
    "evidence_tier": ["1", "2", "3"],
    "venue_type": [
        "religious_site", "school", "university", "entertainment", "retail",
        "transit", "public_space", "residence", "government", "workplace",
        "healthcare", "rural", "multi_site", "other", "political", "political_rally",
    ],
    "target_type": [
        "religious", "ethnic", "lgbtq", "women", "political", "school_random",
        "university_random", "random_public", "workplace", "family", "police",
        "disabled_persons", "community", "mixed", "other",
    ],
}

# All other fields: treat as free-text strings.
```

## Special handling

### `event_date`
Parse as ISO `YYYY-MM-DD` into a date column. If only `YYYY-MM` provided (some foiled plots), set day to 01 and flag.

### `evidence_tier`
Schema shows this as integer (1|2|3). Cast to int. If unknown → null.

### `ideology_contested`
Some rows have this field, some don't. Default to `N` if absent.

### `case_id` uniqueness
Uniqueness must hold. If duplicates found → log to validation report, keep first.

### Missing required fields
Required: `case_id`, `event_date`, `event_year`, `country`, `status`. If any missing → log but don't drop.

### Long-format explode rules
For each field in `LIST_FIELDS`:
- Produce a long-format CSV with columns `case_id`, `field_name` (e.g. `platform`, `subculture_tag`, `citation_target`, etc.), and `position` (0-indexed order within the list).
- Drop empties; strip whitespace.

### `influences.csv` (from part10)
`part10_network_analysis.md` uses a DIFFERENT schema per edge:
```
### NET-XXX
- source_case_id: ...
- target_case_id: ...
- evidence_tier: 1|2|3
- citation_type: ...
- source_attribution: ...
- notes: ...
```
Parse these separately. Output columns: `edge_id`, `source_case_id`, `target_case_id`, `evidence_tier`, `citation_type`, `source_attribution`, `notes`. Also validate that referenced case_ids exist in `cases.csv` — any dangling reference → add to validation report.

### `audit_flags.csv` from `part11`
Extract the 9-row audit table from `part11_audit_and_gaps.md` and preserve as CSV with columns: `flag_id`, `claim`, `status`, `recommended_treatment`.

### `validation_corpus.csv` from `part11`
Extract the validation-corpus case lists (Core far-right, Columbine-fandom, Incel, Kolumbayn, Null, Anomalous) as a long-format CSV: `case_id`, `corpus_category`.

## Example starter script

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["polars>=1.0", "python-dateutil"]
# ///
"""Convert batched OECD mass-violence dataset markdown → Polars-ready CSV/parquet."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import polars as pl

INPUT_DIR = Path(".")  # directory with part*.md files
OUT_DIR = Path("out")
OUT_DIR.mkdir(exist_ok=True)

CASE_HEADER_RE = re.compile(r"^### ([A-Z][A-Z0-9\-_]+)\s*$")
FIELD_RE = re.compile(r"^- ([a-z][a-z0-9_]*): (.*)$")

INT_FIELDS = {
    "event_year", "perp_age", "fatalities_total_incl_perp",
    "fatalities_excl_perp", "total_casualties",
    "incoming_citation_count", "outgoing_citation_count",
    "manifesto_length_pages", "livestream_duration_min",
}

LIST_FIELDS = {
    "subculture_tags", "primary_online_handles", "primary_platforms",
    "named_prior_attackers_incoming", "named_by_subsequent_attackers",
    "cross_references", "key_sources",
}

# Enum domains — see part01 schema for authoritative list
ENUM_FIELDS = {
    "status": {"C", "PF", "F"},
    "perp_sex": {"M", "F", "trans_MtF", "trans_FtM", "mixed"},
    # ... fill in rest
}

@dataclass
class Case:
    case_id: str
    fields: dict[str, str] = field(default_factory=dict)
    source_file: str = ""


def parse_file(path: Path) -> list[Case]:
    cases: list[Case] = []
    current: Case | None = None
    in_case = False
    for line in path.read_text().splitlines():
        header_match = CASE_HEADER_RE.match(line)
        if header_match:
            if current:
                cases.append(current)
            cid = header_match.group(1)
            # Heuristic: case IDs have the form COUNTRY-YEAR-SOMETHING
            if re.match(r"^[A-Z]{2,3}-\d{4}-", cid) or cid.startswith("NET-"):
                current = Case(case_id=cid, source_file=path.name)
                in_case = True
            else:
                current = None
                in_case = False
            continue
        if not in_case or current is None:
            continue
        field_match = FIELD_RE.match(line)
        if field_match:
            k, v = field_match.group(1), field_match.group(2).strip()
            current.fields[k] = v
    if current:
        cases.append(current)
    return cases


def normalize(case: Case) -> dict[str, Any]:
    row: dict[str, Any] = {"case_id": case.case_id, "source_file": case.source_file}
    for k, v in case.fields.items():
        if k in INT_FIELDS:
            try:
                row[k] = int(v)
            except ValueError:
                row[k] = None
        else:
            row[k] = v if v not in ("", "null", "None", "N/A") else None
    return row


def main() -> None:
    event_files = sorted(
        p for p in INPUT_DIR.glob("part0[1-9]*.md")
        if "network" not in p.name and "audit" not in p.name
    )
    event_files += sorted(INPUT_DIR.glob("part10_*.md"))  # handled separately below
    event_files = [p for p in event_files if "network" not in p.name]

    all_cases: list[Case] = []
    for p in event_files:
        all_cases.extend(parse_file(p))

    rows = [normalize(c) for c in all_cases]
    df = pl.DataFrame(rows)
    df.write_csv(OUT_DIR / "cases.csv")
    df.write_parquet(OUT_DIR / "cases.parquet")

    # Long-format explodes
    for lf in LIST_FIELDS:
        if lf not in df.columns:
            continue
        long = (
            df.select(["case_id", lf])
            .drop_nulls(lf)
            .with_columns(pl.col(lf).str.split(";").alias("items"))
            .explode("items")
            .with_columns(pl.col("items").str.strip_chars().alias("value"))
            .filter(pl.col("value") != "")
            .drop([lf, "items"])
        )
        long.write_csv(OUT_DIR / f"{lf}.csv")

    # Network edges from part10
    net_path = INPUT_DIR / "part10_network_analysis.md"
    if net_path.exists():
        edges = parse_file(net_path)
        edge_rows = [
            {"edge_id": e.case_id, **e.fields} for e in edges
            if e.case_id.startswith("NET-")
        ]
        pl.DataFrame(edge_rows).write_csv(OUT_DIR / "influences.csv")

    # TODO: audit_flags.csv + validation_corpus.csv from part11 (markdown table extraction)
    # TODO: validation_report.txt with enum mismatches + dangling case_id references

    print(f"Wrote {df.height} cases to {OUT_DIR}/")


if __name__ == "__main__":
    main()
```

## Acceptance criteria

1. `cases.csv` has one row per case, with ~160 rows total, no duplicate case_ids.
2. All expected columns present; column dtypes match `schema.json`.
3. `influences.csv` has one row per network edge, all `source_case_id` and `target_case_id` values exist in `cases.csv` (dangling ones flagged in validation report).
4. Each `LIST_FIELDS` field produces a long-format CSV.
5. `validation_report.txt` reports: rows missing required fields, enum values that don't match the canonical domain, dangling network references, duplicate case_ids.
6. Running the script is idempotent — rerun produces byte-identical output.
7. Total runtime < 10 seconds on a laptop.

## Non-goals / things NOT to do

- Do NOT try to re-code ideological or aesthetic classifications. The markdown is authoritative.
- Do NOT drop "contested" or "anomalous" cases. They are part of the dataset and dissertation analysis specifically needs them.
- Do NOT "normalize" weapon inscriptions, manifesto titles, or verbatim quotes. Preserve exactly as written, including non-Latin scripts (НЕНАВИСТЬ, БОГ, etc.).
- Do NOT auto-translate non-English text.
- Do NOT assume any missing field means "no". Preserve null/None vs. explicit "N".

## Validation tests the agent should run

```python
# After building cases.csv:
assert df["case_id"].n_unique() == df.height, "Duplicate case IDs"
assert df["event_year"].min() >= 2001
assert df["event_year"].max() <= 2026
assert set(df["status"].unique()) <= {"C", "PF", "F"}

# For influences.csv:
case_ids = set(df["case_id"].to_list())
for edge in influences_df.iter_rows(named=True):
    assert edge["source_case_id"] in case_ids or edge["source_case_id"].startswith("USA-1999-COLUMBINE"), \
        f"Dangling source: {edge['source_case_id']}"
```

## Deliverables to print at end

- Total rows written per table
- List of enum mismatches
- List of dangling case_id references in influences
- List of cases with missing required fields

---

That's it. The markdown files are the source of truth. Build the CSVs exactly as specified.
