# OECD Mass Violence Dataset — Part 10: Network Analysis

This file captures the citation/influence network structure that's hard to express in per-case bullets. Parse this separately; treat as structured relational data to feed into `influences.csv`.

---

## Parsing schema for this file

Each network edge (directional citation of one attacker by another) is a row with these fields:

- `source_case_id` — who was cited
- `target_case_id` — who cited them
- `evidence_tier` — 1=court/coroner/official investigation, 2=multi-source reputable journalism, 3=single-source/contested
- `citation_type` — enum: `manifesto_named` | `weapon_inscribed` | `direct_contact` | `aesthetic_replication` | `structural_cognate` | `anniversary` | `searched_for` | `mentor_relationship` | `coordinated_plot`
- `source_attribution` — short bibliographic note
- `notes` — freeform

Edges are grouped by the "target" case (the citing attacker) because that's how the evidence typically surfaces (in manifestos/searches of a subsequent attacker).

---

## The 2024-2025 Accelerationist Network Pivot

The most important findable contagion chain in the recent period. Transnational, multi-platform, cross-age, cross-gender, cross-ideology. Central node is Kucukyetim (Eskisehir Aug 2024).

### NET-001
- source_case_id: TUR-2024-ESKISEHIR
- target_case_id: USA-2024-MADISON
- evidence_tier: 2
- citation_type: structural_cognate
- source_attribution: ARC "Triangulating Terror" Jan 2025; DOJ Paffendorf indictment Dec 2024
- notes: Rupnow's Terrorgram-adjacent channels overlapped with Kucukyetim's. No direct communication proven but shared community.

### NET-002
- source_case_id: USA-2024-MADISON
- target_case_id: USA-2024-PAFFENDORF
- evidence_tier: 1
- citation_type: coordinated_plot
- source_attribution: DOJ indictment of Alexander Paffendorf Dec 2024
- notes: Rupnow and Paffendorf coordinated parallel attacks via private Discord server. Paffendorf targeted Carlsbad CA government buildings same day as Rupnow's Madison attack. DOJ indictment explicitly documents contact + planning logs.

### NET-003
- source_case_id: TUR-2024-ESKISEHIR
- target_case_id: USA-2025-ANTIOCH
- evidence_tier: 1
- citation_type: mentor_relationship
- source_attribution: Henderson's own manifesto + Discord logs cited in DOJ/MNPD/ADL briefings Jan 2025
- notes: Henderson self-identified Kucukyetim ("Goldson TheDude Sincapgrad" / "Cin Sincap") as his mentor. Discord contact documented.

### NET-004
- source_case_id: USA-2024-MADISON
- target_case_id: USA-2025-ANTIOCH
- evidence_tier: 1
- citation_type: manifesto_named
- source_attribution: Henderson manifesto "The Enemy's Blueprint" + weapon inscriptions
- notes: Rupnow explicitly in Henderson's inscription list.

### NET-005
- source_case_id: USA-2024-MADISON
- target_case_id: USA-2025-MINNEAPOLIS
- evidence_tier: 1
- citation_type: weapon_inscribed
- source_attribution: FBI/MPD post-incident Aug 2025; ADL briefing
- notes: "NATALIE RUPNOW" explicitly inscribed on Westman's weapons. Cleanest attacker-to-attacker citation post-Rupnow.

### NET-006
- source_case_id: USA-2025-ANTIOCH
- target_case_id: USA-2025-CASAP-WI
- evidence_tier: 1
- citation_type: manifesto_named
- source_attribution: Casap manifesto "Accelerate the Collapse"; DOJ affidavit Mar 2025
- notes: Casap explicitly names Henderson as co-inspiration.

### NET-007
- source_case_id: USA-2024-MADISON
- target_case_id: USA-2025-CASAP-WI
- evidence_tier: 1
- citation_type: manifesto_named
- source_attribution: Casap manifesto
- notes: Casap explicitly cites Rupnow.

### NET-008
- source_case_id: TUR-2024-ESKISEHIR
- target_case_id: RUS-2025-ODINTSOVO
- evidence_tier: 1
- citation_type: weapon_inscribed
- source_attribution: Russian IC statements Oct-Nov 2025; ARC briefing
- notes: Timofey K's imitation pistol explicitly inscribed Kucukyetim — the first Russian-language attacker to explicitly cite a Turkish accelerationist. Closes the Russia-West Terrorgram loop.

### NET-009
- source_case_id: SVK-2022-BRATISLAVA
- target_case_id: USA-2025-CASAP-WI
- evidence_tier: 1
- citation_type: manifesto_named
- source_attribution: Casap manifesto
- notes: Krajcik's Terrorgram-canonical status means he is cited in virtually every 2024-2025 accelerationist plot.

### NET-010
- source_case_id: SVK-2022-BENADIK
- target_case_id: SVK-2022-BRATISLAVA
- evidence_tier: 1
- citation_type: mentor_relationship
- source_attribution: ARC 2023; Slovak prosecutors
- notes: Benadik (Slovakbro) was identified as Krajcik's mentor on Terrorgram.

---

## The primary "Saints triumvirate" chain (Breivik-Roof-Tarrant)

### NET-101
- source_case_id: NOR-2011-BREIVIK
- target_case_id: USA-2015-CHARLESTON
- evidence_tier: 2
- citation_type: aesthetic_replication
- source_attribution: Roof manifesto "The Last Rhodesian"
- notes: Structural parallel (manifesto + politicized mass-casualty aspiration). Roof did not name Breivik explicitly.

### NET-102
- source_case_id: NOR-2011-BREIVIK
- target_case_id: NZL-2019-CHRISTCHURCH
- evidence_tier: 1
- citation_type: manifesto_named
- source_attribution: Tarrant manifesto "The Great Replacement"
- notes: Tarrant claims brief email contact with Breivik; court records did not fully verify but manifesto cites Breivik as primary inspiration + acknowledges "blessing" of Knights Templar framework.

### NET-103
- source_case_id: USA-2015-CHARLESTON
- target_case_id: NZL-2019-CHRISTCHURCH
- evidence_tier: 1
- citation_type: manifesto_named
- source_attribution: Tarrant manifesto
- notes: Roof named in Tarrant manifesto's dedication list.

### NET-104
- source_case_id: NZL-2019-CHRISTCHURCH
- target_case_id: USA-2019-POWAY
- evidence_tier: 1
- citation_type: manifesto_named
- source_attribution: Earnest manifesto
- notes: Earnest names Tarrant explicitly as primary model.

### NET-105
- source_case_id: NZL-2019-CHRISTCHURCH
- target_case_id: USA-2019-ELPASO
- evidence_tier: 1
- citation_type: manifesto_named
- source_attribution: Crusius manifesto "The Inconvenient Truth"
- notes: Crusius names Christchurch: "inspired by the Christchurch shooter".

### NET-106
- source_case_id: NZL-2019-CHRISTCHURCH
- target_case_id: DEU-2019-HALLE
- evidence_tier: 1
- citation_type: aesthetic_replication
- source_attribution: Balliet manifesto + Twitch livestream
- notes: Balliet cites Tarrant + Earnest + Bowers + Crusius in order. Gamified helmet-cam + livestream template = direct Tarrant replication.

### NET-107
- source_case_id: NZL-2019-CHRISTCHURCH
- target_case_id: USA-2022-BUFFALO
- evidence_tier: 1
- citation_type: manifesto_named
- source_attribution: Gendron 180-page manifesto (heavily plagiarized from Tarrant)
- notes: Gendron manifesto verbatim-copies large sections of Tarrant's. Primary citation.

### NET-108
- source_case_id: NZL-2019-CHRISTCHURCH
- target_case_id: SVK-2022-BRATISLAVA
- evidence_tier: 1
- citation_type: manifesto_named
- source_attribution: Krajcik "A Call to Arms"; Twitter handle @NTMA0315
- notes: Krajcik self-identifies as "Saint Tarrant's 6th Disciple". Handle literally is "March 15" (Tarrant date).

### NET-109
- source_case_id: USA-2022-BUFFALO
- target_case_id: SVK-2022-BRATISLAVA
- evidence_tier: 1
- citation_type: manifesto_named
- source_attribution: Krajcik "A Call to Arms"
- notes: Krajcik names Gendron as "the final nail in the coffin".

---

## Tarrant's weapon-inscription list (NZ Royal Commission confirmed)

These names were inscribed on Tarrant's firearms and are all documented:

### NET-150
- source_case_id: ITA-2018-MACERATA
- target_case_id: NZL-2019-CHRISTCHURCH
- evidence_tier: 1
- citation_type: weapon_inscribed
- source_attribution: NZ Royal Commission of Inquiry 2020
- notes: "Luca Traini" inscribed on firearm.

### NET-151
- source_case_id: SWE-2015-TROLLHATTAN
- target_case_id: NZL-2019-CHRISTCHURCH
- evidence_tier: 1
- citation_type: weapon_inscribed
- source_attribution: NZ Royal Commission
- notes: "Anton Lundin Pettersson" inscribed.

### NET-152
- source_case_id: CAN-2017-QUEBEC
- target_case_id: NZL-2019-CHRISTCHURCH
- evidence_tier: 1
- citation_type: weapon_inscribed
- source_attribution: NZ Royal Commission
- notes: "Alexandre Bissonnette" inscribed.

### NET-153
- source_case_id: UK-2017-FINSBURY
- target_case_id: NZL-2019-CHRISTCHURCH
- evidence_tier: 1
- citation_type: weapon_inscribed
- source_attribution: NZ Royal Commission
- notes: "Darren Osborne" inscribed.

---

## The Rodger-incel chain

### NET-201
- source_case_id: USA-2014-ISLAVISTA
- target_case_id: CAN-2018-TORONTO
- evidence_tier: 1
- citation_type: manifesto_named
- source_attribution: Minassian Facebook post minutes before attack
- notes: "Supreme Gentleman Elliot Rodger" explicit.

### NET-202
- source_case_id: USA-2014-ISLAVISTA
- target_case_id: UK-2021-PLYMOUTH
- evidence_tier: 1
- citation_type: manifesto_named
- source_attribution: Davison YouTube + Reddit
- notes: Davison explicitly names Rodger.

### NET-203
- source_case_id: USA-2014-ISLAVISTA
- target_case_id: MEX-2025-CCHSUR
- evidence_tier: 1
- citation_type: manifesto_named
- source_attribution: Lex Ashton Discord/X posts in Spanish
- notes: Spanish-language Rodger canon translation.

---

## The Russian Kolumbayn chain

### NET-301
- source_case_id: RUS-2018-KERCH
- target_case_id: RUS-2021-KAZAN
- evidence_tier: 1
- citation_type: aesthetic_replication
- source_attribution: Russian Investigative Committee (Bastrykin Nov 2021)
- notes: IC explicitly named Kolumbayn subcultural trend. БОГ mask + "HATRED" T-shirt lineage.

### NET-302
- source_case_id: RUS-2021-KAZAN
- target_case_id: RUS-2021-PERM
- evidence_tier: 1
- citation_type: manifesto_named
- source_attribution: Bekmansurov VK post "My Anger"
- notes: CLEANEST textual citation in Russian Kolumbayn chain. Bekmansurov explicitly cites Galyaviev by name.

### NET-303
- source_case_id: RUS-2018-KERCH
- target_case_id: RUS-2022-IZHEVSK
- evidence_tier: 2
- citation_type: aesthetic_replication
- source_attribution: Russian IC statements; Kazantsev's HATE-inscribed magazines + Harris/Klebold keychains
- notes: Aesthetic replication; Roslyakov T-shirt language ("HATE") replicated.

### NET-304
- source_case_id: RUS-2018-KERCH
- target_case_id: CZE-2023-PRAGUE
- evidence_tier: 2
- citation_type: structural_cognate
- source_attribution: Czech Police + iROZHLAS; Kozak's Telegram channel subscriptions
- notes: Kozak subscribed to Russian-language Kolumbayn Telegram channels explicitly covering Kazan + Izhevsk + Afanaskina cases.

### NET-305
- source_case_id: RUS-2018-KERCH
- target_case_id: RUS-2025-ODINTSOVO
- evidence_tier: 2
- citation_type: aesthetic_replication
- source_attribution: Russian IC; ARC briefing
- notes: НЕНАВИСТЬ iconography persists. Kolumbayn tradition actively invoked.

---

## The Columbine fandom / TCC chain (US)

### NET-401
- source_case_id: USA-2012-SANDYHOOK
- target_case_id: USA-2023-NASHVILLE
- evidence_tier: 2
- citation_type: searched_for
- source_attribution: MNPD + TBI-released materials 2025
- notes: Hale's writings extensively reference Sandy Hook alongside Columbine.

### NET-402
- source_case_id: USA-2012-SANDYHOOK
- target_case_id: USA-2024-MADISON
- evidence_tier: 1
- citation_type: searched_for
- source_attribution: ADL Dec 2024; DOJ affidavit
- notes: Rupnow's research explicitly referenced Lanza/Sandy Hook among TCC canon.

### NET-403
- source_case_id: USA-2012-SANDYHOOK
- target_case_id: USA-2025-MINNEAPOLIS
- evidence_tier: 1
- citation_type: searched_for
- source_attribution: FBI/MPD briefings Aug 2025
- notes: Westman references.

### NET-404
- source_case_id: USA-2018-PARKLAND
- target_case_id: USA-2025-ANTIOCH
- evidence_tier: 1
- citation_type: manifesto_named
- source_attribution: Henderson manifesto
- notes: Cruz named.

### NET-405
- source_case_id: USA-1999-COLUMBINE (out of dataset scope, pre-OECD window)
- target_case_id: [many cases]
- evidence_tier: 1
- citation_type: searched_for
- source_attribution: multiple
- notes: Out-of-scope for OECD 2001-2026 dataset; include as exogenous anchor: Columbine 1999 (Harris/Klebold) is the universal substrate for most school-shooter cases in this dataset. The task brief treats Columbine as a pre-dataset anchor.

---

## The Japanese JP-contagion chains

### NET-501
- source_case_id: JPN-2001-IKEDA
- target_case_id: JPN-2008-AKIHABARA
- evidence_tier: 2
- citation_type: anniversary
- source_attribution: Japanese press commentary
- notes: Exactly 7 years to day. Widely noted as anniversary but no textual citation.

### NET-502
- source_case_id: JPN-2019-KYOANI
- target_case_id: JPN-2021-TOKUSHIMAACTY
- evidence_tier: 1
- citation_type: manifesto_named
- source_attribution: Tokushima prosecutors; perpetrator Shigeru Okada told police "imitating the Kyoto Animation incident"
- notes: Japanese arson contagion. Okada's Tokushima Acty Annex attack March 2021.

### NET-503
- source_case_id: JPN-2022-ABE
- target_case_id: JPN-2023-KISHIDA
- evidence_tier: 3
- citation_type: structural_cognate
- source_attribution: Japanese court assessment — NOT explicit citation. Kimura refused to speak with police.
- notes: Structural parallel (same target class, DIY internet weapon, 9-month interval). Widely assumed inferential link.

### NET-504
- source_case_id: JPN-2021-ODAKYU
- target_case_id: JPN-2021-KEIO
- evidence_tier: 1
- citation_type: manifesto_named
- source_attribution: Japanese court
- notes: Hattori court-documented cited Odakyu as inspiration.

### NET-505
- source_case_id: JPN-2008-AKIHABARA
- target_case_id: USA-2012-SANDYHOOK
- evidence_tier: 1
- citation_type: searched_for
- source_attribution: CT State's Attorney Sedensky Report Nov 2013; OCA report 2014
- notes: Lanza's spreadsheet catalog of ~500 mass murderers explicitly included Kato Akihabara. Cleanest JP→US contagion link at consumption level.

---

## The Korean 묻지마 cluster

### NET-601
- source_case_id: KOR-2023-SILLIM
- target_case_id: KOR-2023-BUNDANG
- evidence_tier: 1
- citation_type: searched_for
- source_attribution: Korean police confirmation
- notes: Choi searched Sillim coverage before rampage.

---

## The vehicle-ramming contagion (Nice 2016 template)

### NET-701
- source_case_id: FRA-2016-NICE
- target_case_id: DEU-2016-BERLIN
- evidence_tier: 2
- citation_type: aesthetic_replication
- source_attribution: Bundestag investigative committee report 2021
- notes: Structural template replication; 6-month delay.

### NET-702
- source_case_id: FRA-2016-NICE
- target_case_id: CAN-2018-TORONTO
- evidence_tier: 2
- citation_type: aesthetic_replication
- source_attribution: general press consensus
- notes: Method replication; Minassian's own ideological framing (incel) differs.

### NET-703
- source_case_id: FRA-2016-NICE
- target_case_id: DEU-2024-MAGDEBURG
- evidence_tier: 2
- citation_type: aesthetic_replication
- source_attribution: press consensus
- notes: Anomalous because Al-Abdulmohsen ideology is anti-Islam. Method-only contagion.

---

## The Traini (Macerata 2018) aesthetic

### NET-801
- source_case_id: ITA-2018-MACERATA
- target_case_id: NZL-2019-CHRISTCHURCH
- evidence_tier: 1
- citation_type: weapon_inscribed + manifesto_named
- source_attribution: NZ Royal Commission; Tarrant manifesto
- notes: Single most canonical Italian→NZ link.
