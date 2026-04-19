# OECD Mass Violence Dataset — Bundle README

**Compiled**: April 2026
**Scope**: ~160 mass-violence events in OECD countries, 2001–2026
**Framing**: aesthetic-contagion primary lens; ideological classification secondary
**Purpose**: Ch. 3 "Saints Score" empirical chapter dataset for dissertation on computational political religion

## Files in this bundle

| File | Contents | ~Lines |
|------|----------|-------|
| `part01_schema_and_2001-2015.md` | Full schema + variable dictionary + source hierarchy + 17 cases 2001–2015 | 800 |
| `part02_2016-2017.md` | 20 cases 2016–2017 | 615 |
| `part03_2018-2019.md` | 22 cases 2018–2019 (Christchurch year) | 884 |
| `part04_2020-2021.md` | 22 cases 2020–2021 | 749 |
| `part05_2022.md` | 12 cases 2022 (Buffalo, Bratislava, Wieambilla) | 443 |
| `part06_2023.md` | 20 cases 2023 (Prague, Nashville, Jacksonville) | 716 |
| `part07_2024.md` | 14 cases 2024 (Eskisehir, Rupnow, Southport) | 493 |
| `part08_2025-2026.md` | 14 cases 2025–2026 (Henderson, Örebro, Graz, Odintsovo) | 516 |
| `part09_foiled_plots.md` | 16 foiled pre-attack plots (Humber/Allison, Paffendorf, Casap) | ~500 |
| `part10_network_analysis.md` | Directional citation/influence network edges — DIFFERENT schema | ~350 |
| `part11_audit_and_gaps.md` | 9 audit corrections + data gaps + validation corpus | ~200 |
| `part12_conversion_prompt.md` | **Prompt to hand to coding agent** for CSV/JSON conversion | ~250 |

## How to use

1. **Review the schema** in `part01` (top ~100 lines).
2. **Parse the 9 audit corrections** in `part11` — these are flagged citation claims from the original research task briefs that did NOT hold up to primary-source verification and should NOT be treated as documented contagion links.
3. **Hand `part12_conversion_prompt.md`** together with all the `part0X.md` files to a coding agent (Alex's stack: OpenCode CLI + Devstral). That prompt specifies exactly how to convert the markdown into `cases.csv`, `influences.csv`, and auxiliary long-format tables.

## Known limitations

- Geographic coverage: heavy on US/Europe/Japan/Russia/Korea/Australia. Thin on Latin American OECD members, Baltic states, Greece/Portugal.
- Most recent cases (Odintsovo Oct 2025, Anapa Feb 2026) have limited primary-source documentation.
- Russian juvenile cases (Afanaskina, Timofey K, Orda) have publication restrictions limiting evidence transparency.
- Evidence tiers are conservative — 1 = court/coroner/official only.

## Key framing decisions

- **Aesthetic contagion is primary**: visual/material replication (weapons inscriptions, clothing, livestream formats, manifesto structures) is the central analytical object.
- **Ideology is secondary**: assessed/claimed/contested variables capture the multi-dimensional nature.
- **Cross-traditional cases highlighted**: Rupnow (Columbine-fandom + Terrorgram), Henderson (TCC + accelerationist + groyper), Timofey K (Kolumbayn + Terrorgram), Westman (TCC + anti-Catholic + gender-politicized).
- **Null case preserved**: Paddock Las Vegas 2017 deliberately retained as falsification case for Saints Score (high kill count, zero ideology/aesthetic signature).
- **Anomaly cases preserved**: Magdeburg 2024 (anti-Islam ex-Muslim attacks Christmas market) and Cauchi Bondi 2024 (schizophrenic attacker, inquest rejected incel framing) intentionally kept as stress-tests.

## Task tracking

Satisfies Dissertation Tracker task `Ch3 Saints Score: Build dataset of attacker canonization events` (page 334b96393f1381e6b7b2f076176e3b27, due 2027-04-01).
