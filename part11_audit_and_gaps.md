# OECD Mass Violence Dataset — Part 11: Audit, Gaps & Validation

Companion documentation for the dataset. Parse as informational, not per-case rows.

---

## 1. Audit flags (9 task-brief claims flagged as unsupported)

Full table of task-brief citation claims that did NOT hold up to primary-source verification, with recommended downgrades.

| # | Claim (as in original briefs) | Status | Recommended treatment |
|---|-------------------------------|--------|----------------------|
| 1 | Kato Akihabara 2008 → Minassian Toronto 2018 textual citation | UNSUPPORTED | Minassian cited Rodger + "4chan Sgt" in court-filed materials, not Kato. Structural cognate only. Consumption-level JP→US contagion IS documented via Lanza (Sandy Hook catalog included Kato). |
| 2 | Uematsu Sagamihara 2016 → Tarrant Christchurch 2019 textual citation | UNSUPPORTED | Tarrant manifesto names Breivik, Roof, Traini, Lundin Pettersson, Lapshyn, Osborne, Bissonnette, Akerlund. Uematsu is not named. Structural cognate only. |
| 3 | Tsushima Odakyu 2021 → Rodger textual citation | UNSUPPORTED | Not confirmed in English-language court coverage. Motive statement "saw a happy woman ~6 years ago" is thematically incel but does not name Rodger. Structural parallel. |
| 4 | Hattori Keio Joker 2021 → Holmes Aurora direct reference | UNSUPPORTED | Holmes' own "Joker" attribution is retracted NYPD-relayed rumor (Dark Knight Rises villain was Bane). Hattori's costume is clearly from 2019 Phillips/Phoenix "Joker" film. Second-order mythic Joker-memory only; no Holmes citation. |
| 5 | Afanaskina Bryansk 2023 → Hale/Klebold "internet diary" | RETRACTED | Russian investigators determined the "internet diary" was FABRICATED (uploaded after her death). No verified Hale admiration trail exists. Downgrade to ALLEGED/UNVERIFIED. |
| 6 | Wieambilla Trains 2022 → Waco/Branch Davidian aesthetic | PARTIAL | Camouflaged bunker confirmed; direct Waco iconography in Train videos was not found in English primary sources. Recommend Queensland Coroner transcripts (Terry Ryan 5-week inquest 2024). |
| 7 | Kretschmer Winnenden 2009 → Krautchan "Bernd from Bavaria" chat | OFFICIALLY RETRACTED | German police officially retracted initial announcement. Treat as false. |
| 8 | Kimura Kishida 2023 → Yamagami textual citation | STRUCTURAL ONLY | Kimura refused to speak with police. Behavioral/thematic parallel only (same target class, same DIY-internet construction logic, 9-month interval). Flag as inferential. |
| 9 | Crépol 2023 "on est là pour tuer les Blancs" quote | UNSUPPORTED | Eyewitness only, politically weaponized, not judicially confirmed. Flag ALLEGED. |

---

## 2. Data gaps

### Countries with thin coverage
- **Mexico**: only ~5 cases captured (Monterrey 2017, UTEG 2024, CCH Sur 2025; plus a few cartel-adjacent events excluded for scope). Latin American OECD members underrepresented.
- **Chile**: no cases meeting threshold in post-Breivik window.
- **Colombia**: joined OECD in 2020; political violence cases predate coverage window or fall outside school/mass-attack typology.
- **Costa Rica**: no cases meeting threshold.
- **Greece**: one plot mentioned in Europol TE-SAT but no completed attack; minimal.
- **Portugal**: minimal.
- **Baltic states** (Estonia, Latvia, Lithuania): no cases meeting threshold. Europol TE-SAT 2023-2025 list several accelerationist/O9A-adjacent arrests (not included here).
- **Slovenia / Croatia**: no cases meeting threshold.
- **Turkey cases beyond Eskisehir**: thin on completed attacks; IS-directed Reina Istanbul 2017 covered; PKK/TAK bombings 2016 covered. Additional Turkish-language sourcing needed for minor attacks.
- **Korean-language sources**: beyond Sillim/Bundang-2023, thin. Daegu subway arson 2003 (192 dead) is pre-window precursor worth noting but pre-2001/out-of-scope for current framing.
- **Hungary / Czechia beyond Prague 2023**: minimal.

### Evidence gaps within covered cases
- Wieambilla 2022 — Queensland Coroner final report pending (inquest concluded 2024).
- Afanaskina Bryansk 2023 — "internet diary" fabrication confirmed but full investigative transparency report not public.
- Eskisehir 2024 — Turkish prosecution files not yet published; ARC briefings used as secondary.
- Rupnow 2024 — full manifesto + Discord diary leaks not yet validated against DOJ evidence exhibits (trial filings pending).
- Henderson 2025 — full manifesto "The Enemy's Blueprint" leaked fragments; full text not yet in public court record.
- Odintsovo 2025 — Russian IC has released statements but juvenile file restrictions limit published detail.
- Anapa 2026 — very recent; preliminary press reporting only.

### Structural gaps
- **Pre-2001 anchor events**: Columbine 1999, Port Arthur 1996, Dunblane 1996, Oklahoma City 1995 are referenced throughout as canon anchors but are outside the dataset window. Note as exogenous references in the network analysis file.
- **Proto-incel before Rodger**: George Sodini Pittsburgh 2009, Marc Lépine Polytechnique 1989. Sodini is in-window but below-threshold (3 dead + self); Lépine predates dataset window.
- **Veterans Day / Orlando Pulse pre-echoes**: any patterns of lone-actor domestic terror by US military personnel deserve separate treatment.

---

## 3. Validation corpus (Saints Score calibration)

The following cases are explicitly flagged as `saints_canon_validation_corpus: Y` — they are the primary positive-class calibration corpus for the Saints Score dissertation chapter.

### Core far-right accelerationist validation corpus
- NOR-2011-BREIVIK
- USA-2015-CHARLESTON (Roof)
- NZL-2019-CHRISTCHURCH (Tarrant)
- USA-2019-POWAY (Earnest)
- USA-2019-ELPASO (Crusius)
- DEU-2019-HALLE (Balliet)
- USA-2018-PITTSBURGH (Bowers)
- USA-2022-BUFFALO (Gendron)
- SVK-2022-BRATISLAVA (Krajcik)
- USA-2025-ANTIOCH (Henderson)
- RUS-2025-ODINTSOVO (Timofey K)

### Columbine fandom / TCC validation corpus
- USA-2012-SANDYHOOK (Lanza)
- USA-2024-MADISON (Rupnow)
- USA-2025-MINNEAPOLIS (Westman — Rupnow citation is the cleanest intra-Columbine-fandom propagation in dataset)

### Incel validation corpus
- USA-2014-ISLAVISTA (Rodger)
- CAN-2018-TORONTO (Minassian)

### Kolumbayn validation corpus
- RUS-2018-KERCH (Roslyakov)
- RUS-2021-KAZAN (Galyaviev — cleanest IC-ruled Kolumbayn attribution)
- RUS-2021-PERM (Bekmansurov — cleanest textual citation of prior Kolumbayn saint)

### Paradigmatic NULL case
- USA-2017-LASVEGAS (Paddock) — deadliest mass shooting in US history but no coherent ideology, no manifesto, no aesthetic-contagion signature. Essential falsification case: Saints Score should be very low here, despite high kill count.

### Ideologically anomalous / "failure mode" cases
- AUT-2015-GRAZ-SUV (Rizvanović — silent, deleted social, schizoid)
- CAN-2020-NOVASCOTIA (Wortman — replica RCMP uniform but no extremist ideology)
- DEU-2024-MAGDEBURG (Al-Abdulmohsen — ex-Muslim pro-AfD anti-Islam Christmas-market attacker, inverted ideology for the venue-type's usual profile)

These anomalous cases are the dissertation's stress-test set: any Saints Score model needs to NOT falsely elevate them.

---

## 4. Coverage metrics (rough)

- Total cases in dataset: ~144 across parts 1-8 (completed/attempted) + ~16 in part 9 (foiled) ≈ **160 cases**.
- Geographic coverage: ~24 OECD countries represented.
- Time window: 2001-01 through 2026-02.
- Completed attacks: ~138
- Failed/attempted attacks (PF): ~10
- Foiled pre-attack (F): ~16
- Ideologically confirmed far-right/accelerationist: ~40
- Jihadist-inspired: ~25
- Incel / misogynist: ~7
- Columbine-fandom / Kolumbayn: ~15
- No ideology / mental-health / personal-grievance: ~40
- Mixed / contested: ~30
