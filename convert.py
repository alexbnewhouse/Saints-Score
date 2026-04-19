#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["polars>=1.0"]
# ///
"""Convert batched OECD mass-violence dataset markdown → Polars-ready CSV/parquet."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import polars as pl

INPUT_DIR = Path(".")
OUT_DIR = Path("out")
OUT_DIR.mkdir(exist_ok=True)

# --- Regex patterns ---
CASE_HEADER_RE = re.compile(r"^### ([A-Z][A-Z0-9\-_]+)\s*$")
FIELD_RE = re.compile(r"^- ([a-z][a-z0-9_]*): (.*)$")

# --- Field type manifests ---
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

ENUM_FIELDS: dict[str, set[str]] = {
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

REQUIRED_FIELDS = {"case_id", "event_date", "event_year", "country", "status"}

# Enum fields that commonly carry parenthetical annotations:
# e.g. "Y (autism)" → enum_value="Y", detail="autism"
ANNOTATED_ENUM_RE = re.compile(r"^([A-Za-z_]+)\s*\((.+)\)\s*$")

# Explicit remaps for values that don't match any enum but have a clear mapping
ENUM_REMAPS: dict[str, dict[str, str]] = {
    "saints_tradition": {
        "accelerationist": "core_farright",  # closest canonical tradition
    },
    "target_type": {
        "government": "political",  # government targets → political enum value
    },
}

# Long-format output names per LIST_FIELD
LIST_FIELD_VALUE_NAME: dict[str, str] = {
    "subculture_tags": "subculture_tag",
    "primary_online_handles": "handle",
    "primary_platforms": "platform",
    "named_prior_attackers_incoming": "cited_attacker",
    "named_by_subsequent_attackers": "citing_attacker",
    "cross_references": "source_dataset",
    "key_sources": "source",
}

# Long-format output filenames per LIST_FIELD
LIST_FIELD_FILENAME: dict[str, str] = {
    "subculture_tags": "subculture_tags.csv",
    "primary_online_handles": "primary_online_handles.csv",
    "primary_platforms": "platforms.csv",
    "named_prior_attackers_incoming": "named_prior_attackers_incoming.csv",
    "named_by_subsequent_attackers": "named_by_subsequent_attackers.csv",
    "cross_references": "cross_references.csv",
    "key_sources": "key_sources.csv",
}


@dataclass
class Case:
    case_id: str
    fields: dict[str, str] = field(default_factory=dict)
    source_file: str = ""


# --- Validation report accumulator ---
validation_lines: list[str] = []


def log_validation(category: str, msg: str) -> None:
    validation_lines.append(f"[{category}] {msg}")


def parse_file(path: Path) -> list[Case]:
    """Parse a markdown file into a list of Case objects."""
    cases: list[Case] = []
    current: Case | None = None
    in_case = False

    for line in path.read_text(encoding="utf-8").splitlines():
        header_match = CASE_HEADER_RE.match(line)
        if header_match:
            if current:
                cases.append(current)
            cid = header_match.group(1)
            # Case IDs: COUNTRY-YEAR-NAME  or  NET-XXX
            if re.match(r"^[A-Z]{2,4}-\d{4}-", cid) or cid.startswith("NET-"):
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


def normalize_case(case: Case) -> dict[str, Any]:
    """Convert a Case into a flat dict with proper types."""
    row: dict[str, Any] = {"case_id": case.case_id, "source_file": case.source_file}

    for k, v in case.fields.items():
        raw = v.strip()

        # Null-like values → None (but preserve explicit strings like "N" or "none")
        if raw in ("", "null", "None", "N/A", "n/a", "unknown"):
            if k in INT_FIELDS:
                row[k] = None
            elif k in ENUM_FIELDS:
                row[k] = None
            else:
                row[k] = None
            continue

        # Integer fields
        if k in INT_FIELDS:
            # Strip any non-numeric prefix/suffix like "~" or "+"
            cleaned = re.sub(r"[^\d\-]", "", raw)
            if cleaned:
                try:
                    row[k] = int(cleaned)
                except ValueError:
                    row[k] = None
                    log_validation("INT_PARSE", f"{case.case_id}: field '{k}' value '{raw}' not parseable as int")
            else:
                row[k] = None
            continue

        # evidence_tier: cast to int
        if k == "evidence_tier":
            cleaned = raw.strip()
            if cleaned in ("1", "2", "3"):
                row[k] = cleaned  # keep as string for enum validation, cast later
            else:
                row[k] = cleaned
            # fall through to enum validation below handled separately
            # Actually, handle inline:
            if cleaned not in ENUM_FIELDS.get("evidence_tier", set()):
                log_validation("ENUM_MISMATCH", f"{case.case_id}: field 'evidence_tier' value '{cleaned}' not in {sorted(ENUM_FIELDS['evidence_tier'])}")
            continue

        # Enum fields (validate)
        if k in ENUM_FIELDS:
            if raw not in ENUM_FIELDS[k]:
                log_validation("ENUM_MISMATCH", f"{case.case_id}: field '{k}' value '{raw}' not in {sorted(ENUM_FIELDS[k])}")
            row[k] = raw
            continue

        # Everything else: free-text string
        row[k] = raw

    # Default ideology_contested to N if absent
    if "ideology_contested" not in row:
        row["ideology_contested"] = "N"

    return row


def parse_date(val: str | None) -> str | None:
    """Parse event_date to ISO YYYY-MM-DD string. Flag partial dates."""
    if val is None:
        return None
    val = val.strip()
    if not val or val in ("null", "None", "N/A", "unknown"):
        return None
    # Full date YYYY-MM-DD
    if re.match(r"^\d{4}-\d{2}-\d{2}$", val):
        return val
    # Partial YYYY-MM
    if re.match(r"^\d{4}-\d{2}$", val):
        log_validation("PARTIAL_DATE", f"Date '{val}' has no day; set to 01")
        return val + "-01"
    # Partial YYYY only
    if re.match(r"^\d{4}$", val):
        log_validation("PARTIAL_DATE", f"Date '{val}' has no month/day; set to 01-01")
        return val + "-01-01"
    return val


def build_cases(input_dir: Path) -> pl.DataFrame:
    """Parse all event files and build the wide cases DataFrame."""
    # Event case files: part01-part09 (skip part10=network, part11=audit, part12=prompt)
    event_files = sorted(
        p for p in input_dir.glob("part*.md")
        if not any(skip in p.name for skip in ("part10", "part11", "part12"))
    )

    all_cases: list[Case] = []
    for p in event_files:
        cases = parse_file(p)
        # Filter out any NET- edges that might appear
        cases = [c for c in cases if not c.case_id.startswith("NET-")]
        all_cases.extend(cases)

    # Check for duplicate case_ids
    seen: dict[str, int] = {}
    deduped: list[Case] = []
    for c in all_cases:
        if c.case_id in seen:
            log_validation("DUPLICATE_CASE_ID", f"Duplicate case_id '{c.case_id}' in {c.source_file} (first seen in file index {seen[c.case_id]}). Keeping first.")
        else:
            seen[c.case_id] = len(deduped)
            deduped.append(c)
    all_cases = deduped

    # Normalize
    rows = [normalize_case(c) for c in all_cases]

    # Parse dates
    for row in rows:
        row["event_date"] = parse_date(row.get("event_date"))

    # Check required fields
    for row in rows:
        for rf in REQUIRED_FIELDS:
            if rf not in row or row[rf] is None:
                log_validation("MISSING_REQUIRED", f"{row['case_id']}: missing required field '{rf}'")

    # Collect all column names across rows
    all_cols: dict[str, int] = {}
    for row in rows:
        for k in row:
            if k not in all_cols:
                all_cols[k] = 0
            all_cols[k] += 1

    # Ensure every row has all columns
    for row in rows:
        for col in all_cols:
            if col not in row:
                row[col] = None

    # Build schema: int fields → Int64, everything else → Utf8
    col_schema: dict[str, pl.DataType] = {}
    for col in all_cols:
        if col in INT_FIELDS:
            col_schema[col] = pl.Int64
        else:
            col_schema[col] = pl.Utf8
    df = pl.DataFrame(rows, schema=col_schema, infer_schema_length=None)

    # Cast evidence_tier to Int64
    if "evidence_tier" in df.columns:
        df = df.with_columns(pl.col("evidence_tier").cast(pl.Int64, strict=False))

    # Cast event_date to Date
    if "event_date" in df.columns:
        df = df.with_columns(pl.col("event_date").str.to_date("%Y-%m-%d", strict=False))

    # Sort by event_date for deterministic output
    if "event_date" in df.columns:
        df = df.sort("event_date", nulls_last=True)

    return df


def build_long_format_tables(df: pl.DataFrame) -> dict[str, pl.DataFrame]:
    """Explode LIST_FIELDS into long-format auxiliary tables."""
    tables: dict[str, pl.DataFrame] = {}

    for lf in sorted(LIST_FIELDS):
        if lf not in df.columns:
            continue
        fname = LIST_FIELD_FILENAME[lf]
        value_name = LIST_FIELD_VALUE_NAME[lf]

        # Get rows with non-null values
        sub = df.select(["case_id", lf]).drop_nulls(lf)
        if sub.height == 0:
            tables[fname] = pl.DataFrame({"case_id": [], value_name: [], "position": []}).cast({"position": pl.Int64})
            continue

        # Split on semicolons
        sub = sub.with_columns(pl.col(lf).str.split(";").alias("_items"))
        sub = sub.explode("_items")
        sub = sub.with_columns(pl.col("_items").str.strip_chars().alias(value_name))
        sub = sub.filter(pl.col(value_name) != "")

        # Add position (0-indexed within each case)
        sub = sub.with_columns(
            pl.lit(1).cum_sum().over("case_id").alias("position") - 1
        )
        sub = sub.select(["case_id", value_name, "position"])
        tables[fname] = sub

    return tables


def build_influences(input_dir: Path, case_ids: set[str]) -> pl.DataFrame:
    """Parse part10 network edges into influences DataFrame."""
    net_path = input_dir / "part10_network_analysis.md"
    if not net_path.exists():
        log_validation("MISSING_FILE", "part10_network_analysis.md not found")
        return pl.DataFrame()

    edges = parse_file(net_path)
    edge_rows: list[dict[str, Any]] = []

    for e in edges:
        if not e.case_id.startswith("NET-"):
            continue
        row: dict[str, Any] = {"edge_id": e.case_id}
        for col in ("source_case_id", "target_case_id", "evidence_tier",
                     "citation_type", "source_attribution", "notes"):
            val = e.fields.get(col)
            if val and val.strip() in ("", "null", "None"):
                val = None
            row[col] = val.strip() if val else None

        # Cast evidence_tier to int
        if row.get("evidence_tier"):
            try:
                row["evidence_tier"] = int(row["evidence_tier"])
            except ValueError:
                row["evidence_tier"] = None

        edge_rows.append(row)

    if not edge_rows:
        return pl.DataFrame()

    inf_df = pl.DataFrame(edge_rows)

    # Validate references
    # Allow pre-dataset anchors like USA-1999-COLUMBINE
    for row in edge_rows:
        for ref_col in ("source_case_id", "target_case_id"):
            ref = row.get(ref_col)
            if ref and ref not in case_ids:
                # Check if it looks like a pre-dataset reference
                m = re.match(r"^[A-Z]{2,4}-(\d{4})-", ref)
                if m and int(m.group(1)) < 2001:
                    log_validation("DANGLING_REF_PREDATASET", f"influences edge {row['edge_id']}: {ref_col}='{ref}' is pre-dataset anchor (OK but not in cases.csv)")
                else:
                    # Check for special "[many cases]" style
                    if ref.startswith("[") or ref == "":
                        log_validation("DANGLING_REF_SPECIAL", f"influences edge {row['edge_id']}: {ref_col}='{ref}' is a special/placeholder reference")
                    else:
                        log_validation("DANGLING_REF", f"influences edge {row['edge_id']}: {ref_col}='{ref}' not found in cases.csv")

    return inf_df


def build_audit_flags(input_dir: Path) -> pl.DataFrame:
    """Extract the 9-row audit table from part11."""
    path = input_dir / "part11_audit_and_gaps.md"
    if not path.exists():
        log_validation("MISSING_FILE", "part11_audit_and_gaps.md not found")
        return pl.DataFrame()

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    # Find the markdown table
    rows: list[dict[str, str]] = []
    in_table = False
    header_seen = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("| #"):
            in_table = True
            header_seen = True
            continue
        if in_table and stripped.startswith("|---"):
            continue
        if in_table and stripped.startswith("|"):
            parts = [p.strip() for p in stripped.split("|")]
            # Filter empty strings from split
            parts = [p for p in parts if p or parts.index(p) not in (0, len(parts) - 1)]
            parts = [p for p in parts if p != ""]
            if len(parts) >= 4:
                rows.append({
                    "flag_id": parts[0],
                    "claim": parts[1],
                    "status": parts[2],
                    "recommended_treatment": parts[3],
                })
        elif in_table and not stripped.startswith("|"):
            break

    if not rows:
        log_validation("AUDIT_PARSE", "Could not parse audit flags table from part11")
        return pl.DataFrame()

    return pl.DataFrame(rows)


def build_validation_corpus(input_dir: Path) -> pl.DataFrame:
    """Extract validation-corpus case lists from part11."""
    path = input_dir / "part11_audit_and_gaps.md"
    if not path.exists():
        return pl.DataFrame()

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    # Category mapping from section headers
    category_map: dict[str, str] = {
        "Core far-right accelerationist validation corpus": "core_farright",
        "Columbine fandom / TCC validation corpus": "columbine_fandom",
        "Incel validation corpus": "incel",
        "Kolumbayn validation corpus": "kolumbayn",
        "Paradigmatic NULL case": "null",
        "Ideologically anomalous / \"failure mode\" cases": "anomalous",
        "Ideologically anomalous / \u201cfailure mode\u201d cases": "anomalous",
    }

    rows: list[dict[str, str]] = []
    current_category: str | None = None

    for line in lines:
        stripped = line.strip()
        # Check for section headers (### level)
        if stripped.startswith("### "):
            header = stripped[4:].strip()
            matched = False
            for pattern, cat in category_map.items():
                if pattern in header or header in pattern:
                    current_category = cat
                    matched = True
                    break
            if not matched:
                current_category = None
            continue

        # Look for case IDs in bullet lines
        if current_category and stripped.startswith("- "):
            # Extract case_id (first token that matches the pattern)
            m = re.match(r"^- ([A-Z]{2,4}-\d{4}-[A-Z0-9_\-]+)", stripped)
            if m:
                rows.append({
                    "case_id": m.group(1),
                    "corpus_category": current_category,
                })

    return pl.DataFrame(rows)


def build_schema(df: pl.DataFrame) -> dict[str, Any]:
    """Build schema.json with column dtypes and enum domains."""
    schema: dict[str, Any] = {
        "columns": {},
        "enum_domains": {},
    }
    for col in df.columns:
        dtype_str = str(df[col].dtype)
        schema["columns"][col] = dtype_str

    for field_name, domain in sorted(ENUM_FIELDS.items()):
        schema["enum_domains"][field_name] = sorted(domain)

    return schema


def enforce_enums(df: pl.DataFrame) -> pl.DataFrame:
    """Produce an enforced version of the cases DataFrame.

    For each enum column:
    1. Split 'VALUE (annotation)' → clean enum value + _detail column
    2. Apply explicit remaps for known mismatches
    3. Strip trailing annotations like 'none (JP-domestic copycat)' → 'none'
    4. Log any remaining violations
    """
    enforced = df.clone()
    enforcement_lines: list[str] = []

    for field_name, domain in sorted(ENUM_FIELDS.items()):
        if field_name not in enforced.columns:
            continue

        col_series = enforced[field_name].cast(pl.Utf8)
        clean_vals: list[str | None] = []
        detail_vals: list[str | None] = []
        remaps = ENUM_REMAPS.get(field_name, {})

        for val in col_series.to_list():
            if val is None:
                clean_vals.append(None)
                detail_vals.append(None)
                continue

            raw = val.strip()
            if raw in ("", "null", "None"):
                clean_vals.append(None)
                detail_vals.append(None)
                continue

            # Already clean
            if raw in domain:
                clean_vals.append(raw)
                detail_vals.append(None)
                continue

            # Check explicit remaps first
            if raw in remaps:
                clean_vals.append(remaps[raw])
                detail_vals.append(f"remapped from '{raw}'")
                enforcement_lines.append(f"[REMAP] {field_name}: '{raw}' → '{remaps[raw]}'")
                continue

            # Try splitting 'VALUE (annotation)'
            m = ANNOTATED_ENUM_RE.match(raw)
            if m:
                core = m.group(1).strip()
                annotation = m.group(2).strip()
                # Check if core matches domain
                if core in domain:
                    clean_vals.append(core)
                    detail_vals.append(annotation)
                    continue
                # Check if core matches a remap
                if core in remaps:
                    clean_vals.append(remaps[core])
                    detail_vals.append(annotation)
                    enforcement_lines.append(f"[REMAP] {field_name}: '{core}' → '{remaps[core]}' (detail: {annotation})")
                    continue

            # Fallback: check if the raw value starts with a valid enum + space
            for dv in sorted(domain, key=len, reverse=True):
                if raw.startswith(dv + " ") or raw.startswith(dv + "+"):
                    clean_vals.append(dv)
                    detail_vals.append(raw[len(dv):].strip().lstrip("(+").rstrip(")").strip())
                    break
            else:
                # Truly unknown — keep raw, log
                clean_vals.append(raw)
                detail_vals.append(None)
                enforcement_lines.append(f"[UNRESOLVED] {field_name}: '{raw}' — no matching enum value")

        # Replace the column with clean values
        enforced = enforced.with_columns(pl.Series(field_name, clean_vals))

        # Add _detail column only if there are any non-null details
        if any(d is not None for d in detail_vals):
            detail_col = f"{field_name}_detail"
            enforced = enforced.with_columns(pl.Series(detail_col, detail_vals))

    return enforced, enforcement_lines


def main() -> None:
    print("Parsing markdown files...")

    # 1. Build cases
    df = build_cases(INPUT_DIR)
    df.write_csv(OUT_DIR / "cases.csv")
    df.write_parquet(OUT_DIR / "cases.parquet")
    print(f"  cases.csv: {df.height} rows, {df.width} columns")

    # 2. Schema
    schema = build_schema(df)
    (OUT_DIR / "schema.json").write_text(json.dumps(schema, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  schema.json: {len(schema['columns'])} columns, {len(schema['enum_domains'])} enum fields")

    # 2b. Enforced version with clean enum columns
    enforced_df, enforcement_lines = enforce_enums(df)
    enforced_df.write_csv(OUT_DIR / "cases_enforced.csv")
    enforced_df.write_parquet(OUT_DIR / "cases_enforced.parquet")
    schema_enforced = build_schema(enforced_df)
    (OUT_DIR / "schema_enforced.json").write_text(
        json.dumps(schema_enforced, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"  cases_enforced.csv: {enforced_df.height} rows, {enforced_df.width} columns")

    # 3. Long-format explodes (from enforced version)
    long_tables = build_long_format_tables(enforced_df)
    for fname, ldf in sorted(long_tables.items()):
        ldf.write_csv(OUT_DIR / fname)
        print(f"  {fname}: {ldf.height} rows")

    # 4. Influences from part10
    case_ids = set(df["case_id"].to_list())
    inf_df = build_influences(INPUT_DIR, case_ids)
    if inf_df.height > 0:
        inf_df.write_csv(OUT_DIR / "influences.csv")
    print(f"  influences.csv: {inf_df.height} rows")

    # 5. Audit flags from part11
    audit_df = build_audit_flags(INPUT_DIR)
    if audit_df.height > 0:
        audit_df.write_csv(OUT_DIR / "audit_flags.csv")
    print(f"  audit_flags.csv: {audit_df.height} rows")

    # 6. Validation corpus from part11
    vc_df = build_validation_corpus(INPUT_DIR)
    if vc_df.height > 0:
        vc_df.write_csv(OUT_DIR / "validation_corpus.csv")
    print(f"  validation_corpus.csv: {vc_df.height} rows")

    # 7. Write validation report
    all_report_lines = validation_lines + ["", "=== ENUM ENFORCEMENT LOG ==="] + enforcement_lines
    (OUT_DIR / "validation_report.txt").write_text("\n".join(all_report_lines) + "\n", encoding="utf-8")
    print(f"  validation_report.txt: {len(validation_lines)} parse entries + {len(enforcement_lines)} enforcement entries")

    # --- Validation assertions ---
    print("\nRunning validation assertions...")
    assert df["case_id"].n_unique() == df.height, "Duplicate case IDs!"
    print(f"  ✓ {df.height} unique case IDs")

    years = df["event_year"].drop_nulls()
    assert years.min() >= 2001, f"Min year {years.min()} < 2001"
    assert years.max() <= 2026, f"Max year {years.max()} > 2026"
    print(f"  ✓ Year range: {years.min()}–{years.max()}")

    statuses = set(df["status"].drop_nulls().unique().to_list())
    assert statuses <= {"C", "PF", "F"}, f"Unexpected statuses: {statuses - {'C', 'PF', 'F'}}"
    print(f"  ✓ Status values: {sorted(statuses)}")

    # Check influences references
    if inf_df.height > 0:
        dangling_sources = []
        dangling_targets = []
        for row in inf_df.iter_rows(named=True):
            src = row.get("source_case_id")
            tgt = row.get("target_case_id")
            if src and src not in case_ids:
                m = re.match(r"^[A-Z]{2,4}-(\d{4})-", src)
                is_pre = m and int(m.group(1)) < 2001
                if not is_pre and not src.startswith("["):
                    dangling_sources.append(src)
            if tgt and tgt not in case_ids:
                m = re.match(r"^[A-Z]{2,4}-(\d{4})-", tgt)
                is_pre = m and int(m.group(1)) < 2001
                if not is_pre and not tgt.startswith("["):
                    dangling_targets.append(tgt)
        if dangling_sources:
            print(f"  ⚠ Dangling source refs in influences: {dangling_sources}")
        if dangling_targets:
            print(f"  ⚠ Dangling target refs in influences: {dangling_targets}")
        if not dangling_sources and not dangling_targets:
            print(f"  ✓ All influence case_id refs valid (pre-dataset anchors noted in report)")

    # --- Summary ---
    print("\n--- Deliverables Summary ---")
    print(f"Total cases: {df.height}")
    for fname, ldf in sorted(long_tables.items()):
        print(f"  {fname}: {ldf.height} rows")
    print(f"  influences.csv: {inf_df.height} rows")
    print(f"  audit_flags.csv: {audit_df.height} rows")
    print(f"  validation_corpus.csv: {vc_df.height} rows")

    # Print enum mismatches
    enum_mismatches = [l for l in validation_lines if "ENUM_MISMATCH" in l]
    if enum_mismatches:
        print(f"\nEnum mismatches ({len(enum_mismatches)}):")
        for m in enum_mismatches:
            print(f"  {m}")
    else:
        print("\nNo enum mismatches found.")

    # Print dangling refs
    dangling = [l for l in validation_lines if "DANGLING_REF" in l]
    if dangling:
        print(f"\nDangling references ({len(dangling)}):")
        for d in dangling:
            print(f"  {d}")

    # Print missing required fields
    missing_req = [l for l in validation_lines if "MISSING_REQUIRED" in l]
    if missing_req:
        print(f"\nMissing required fields ({len(missing_req)}):")
        for m in missing_req:
            print(f"  {m}")
    else:
        print("\nNo missing required fields.")

    # Enforcement summary
    print(f"\n--- Enum Enforcement Summary ---")
    # Verify all enforced enum columns are now clean
    enforced_clean = True
    for field_name, domain in sorted(ENUM_FIELDS.items()):
        if field_name not in enforced_df.columns:
            continue
        col = enforced_df[field_name].drop_nulls()
        if col.len() == 0:
            continue
        violations = [v for v in col.unique().to_list() if v not in domain]
        if violations:
            print(f"  ✗ {field_name}: still has {len(violations)} out-of-domain values: {violations}")
            enforced_clean = False
        else:
            detail_col = f"{field_name}_detail"
            n_detail = 0
            if detail_col in enforced_df.columns:
                n_detail = enforced_df[detail_col].drop_nulls().len()
            if n_detail > 0:
                print(f"  ✓ {field_name}: clean ({col.len()} values) + {n_detail} annotations preserved in {detail_col}")
            else:
                print(f"  ✓ {field_name}: clean ({col.len()} values)")
    if enforced_clean:
        print("\n  ✓ All enum columns fully enforced in cases_enforced.csv")
    else:
        print("\n  ⚠ Some enum columns still have violations (see UNRESOLVED in validation_report.txt)")

    if enforcement_lines:
        remaps = [l for l in enforcement_lines if "REMAP" in l]
        unresolved = [l for l in enforcement_lines if "UNRESOLVED" in l]
        print(f"\n  Remaps applied: {len(remaps)}")
        for r in remaps:
            print(f"    {r}")
        if unresolved:
            print(f"  Unresolved: {len(unresolved)}")
            for u in unresolved:
                print(f"    {u}")

    print("\nDone.")


if __name__ == "__main__":
    main()
