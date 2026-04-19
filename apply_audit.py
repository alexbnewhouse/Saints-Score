"""
Apply audit corrections to cases_enforced.csv based on the comprehensive audit report.

Corrections applied:
1. Evidence tier adjustments for cases with contested/fabricated sources
2. how_disrupted field filled for all PF (partially failed) cases where mechanism is documented
3. Audit flag refinements based on audit recommendations
4. Consistency checks and fixes
"""
import csv
import os
from datetime import datetime

INPUT = "out/cases_enforced.csv"
OUTPUT = "out/cases_audited.csv"

# ── 1. Evidence tier corrections ────────────────────────────────────────────
EVIDENCE_TIER_CHANGES = {
    # Fabricated diary determined by Russian investigators; contested sources
    "RUS-2023-BRYANSK": "2",
}

# ── 2. how_disrupted for PF cases ──────────────────────────────────────────
HOW_DISRUPTED_FILLS = {
    "ESP-2017-BARCELONA": (
        "Alcanar bomb factory accidental explosion forced cell to abandon VBIED plan; "
        "resorted to less-lethal van-ramming"
    ),
    "USA-2019-POWAY": "AR-15 jammed after initial shots; perpetrator fled scene",
    "NOR-2019-BAERUM": (
        "Subdued by worshipper (65-year-old retired Pakistani Air Force officer) "
        "inside Al-Noor Islamic Centre"
    ),
    "DEU-2019-HALLE": (
        "Improvised firearms and explosives malfunctioned; failed to breach "
        "reinforced synagogue door; attacked passersby instead"
    ),
    "UK-2020-STREATHAM": (
        "Shot dead by armed surveillance officers (ongoing MI5 surveillance operation) "
        "within ~60 seconds of initial stabbings"
    ),
    "NZL-2021-LYNNMALL": (
        "Shot dead by undercover police surveillance team within ~60 seconds of attack"
    ),
    "UK-2021-LIVERPOOL": (
        "IED detonated prematurely inside taxi; taxi driver locked doors preventing "
        "egress to Liverpool Women's Hospital; only perpetrator killed"
    ),
    "JPN-2023-KISHIDA": (
        "Pipe bomb failed to detonate fully; perpetrator subdued by bystander "
        "(fisherman) and security"
    ),
    "AUS-2024-WAKELEY": "Subdued by congregation members at Assyrian Christ The Good Shepherd Church",
    "USA-2024-BUTLER": "Shot by Secret Service counter-sniper after initial shots",
    "DEU-2024-MUNICHCONSULATE": "Shot dead by police at scene (Israeli consulate approach)",
    "TUR-2024-ESKISEHIR": (
        "Attack on former school interrupted; perpetrator arrested at scene; "
        "limited casualties due to school hours/response"
    ),
    "RUS-2025-ODINTSOVO": (
        "Juvenile attacker with imitation pistol and knife; limited lethality of weapons; "
        "disruption details subject to Russian juvenile file restrictions"
    ),
    "AUS-2025-BONDIBEACH": (
        "Attack on Bondi Beach Hanukkah ceremony; perpetrators arrested; "
        "preliminary — investigation ongoing"
    ),
    "RUS-2026-ANAPA": (
        "Preliminary; recent incident; disruption mechanism pending official reporting"
    ),
}

# ── 3. Audit flag refinements ──────────────────────────────────────────────
# Append additional context to existing audit_flags where the audit recommends it
AUDIT_FLAG_APPENDS = {
    "RUS-2023-BRYANSK": (
        " Evidence tier downgraded to 2 per audit: fabricated diary confirmed by "
        "Russian investigators."
    ),
    "AUS-2022-WIEAMBILLA": (
        " Pending Queensland Coroner final transcript for Waco iconography verification."
    ),
    "FRA-2023-CREPOL": (
        " Recommend supplementation with judicial records when available."
    ),
}

# ── 4. Consistency: ideology_contested should be Y for contested assessments ─
# Already verified: all cases with 'contested' in ideology_assessed have
# ideology_contested=Y. No changes needed.

def apply_audit(input_path, output_path):
    with open(input_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    changes_log = []

    for row in rows:
        cid = row["case_id"]

        # 1. Evidence tier corrections
        if cid in EVIDENCE_TIER_CHANGES:
            old = row["evidence_tier"]
            new = EVIDENCE_TIER_CHANGES[cid]
            if old != new:
                changes_log.append(f"  {cid}: evidence_tier {old} → {new}")
                row["evidence_tier"] = new

        # 2. how_disrupted fills (only if currently empty)
        if cid in HOW_DISRUPTED_FILLS and not row.get("how_disrupted", "").strip():
            row["how_disrupted"] = HOW_DISRUPTED_FILLS[cid]
            changes_log.append(f"  {cid}: how_disrupted filled")

        # 3. Audit flag appends
        if cid in AUDIT_FLAG_APPENDS:
            existing = row.get("audit_flags", "")
            append_text = AUDIT_FLAG_APPENDS[cid]
            if append_text.strip() not in existing:
                row["audit_flags"] = existing + append_text
                changes_log.append(f"  {cid}: audit_flags appended")

    # Write output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # Print summary
    print(f"Audit corrections applied: {len(changes_log)} changes")
    for line in changes_log:
        print(line)
    print(f"\nOutput written to: {output_path}")
    print(f"Total rows: {len(rows)}")

    # Verification counts
    from collections import Counter
    countries = Counter(r["country"] for r in rows)
    statuses = Counter(r["status"] for r in rows)
    tiers = Counter(r["evidence_tier"] for r in rows)
    pf_with_disrupted = sum(
        1 for r in rows
        if r["status"] == "PF" and r.get("how_disrupted", "").strip()
    )
    pf_total = sum(1 for r in rows if r["status"] == "PF")
    f_with_disrupted = sum(
        1 for r in rows
        if r["status"] == "F" and r.get("how_disrupted", "").strip()
    )
    f_total = sum(1 for r in rows if r["status"] == "F")

    print(f"\n── Verification ──")
    print(f"Countries: {len(countries)} | Cases: {len(rows)}")
    print(f"Status: {dict(statuses)}")
    print(f"Evidence tiers: {dict(sorted(tiers.items()))}")
    print(f"PF how_disrupted coverage: {pf_with_disrupted}/{pf_total}")
    print(f"F how_disrupted coverage: {f_with_disrupted}/{f_total}")


if __name__ == "__main__":
    apply_audit(INPUT, OUTPUT)
