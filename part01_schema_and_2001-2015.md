# OECD Mass Violence Events Dataset — Consolidated Research Data

**Scope**: mass violence events in OECD countries, 2001–2026, both completed and foiled plots.
**Framing**: aesthetic contagion primary lens (visual/material replication priority), ideological classification secondary.
**Status**: consolidated from two research runs (original 90-case dataset + expanded audit with ~60 additions).
**Compiled**: April 2026.

---

## How to parse this file

Each case is a markdown section with header `### CASE_ID` followed by a bullet list of `- field: value` pairs. Fields follow the SCHEMA below. Multi-value fields use semicolons as internal separator. Unknown/unavailable values are `null`. Verbatim inscriptions/quotes appear in double quotes within the value string.

Sections in this file:
1. Schema & variable dictionary
2. Source hierarchy & evidence tiers
3. Audit corrections (9 flagged claims from task briefs)
4. Cases in chronological order (approx. 160 rows)
5. Contagion network — the Rupnow ↔ Küçükyetim ↔ Henderson ↔ Casap ↔ Paffendorf chain
6. Foiled plots section (separate block)
7. Data gaps flagged

---

## 1. Schema & variable dictionary

Core fields (one value per field; semicolons inside a value separate list items):

- `case_id` — unique short ID, format `COUNTRY-YEAR-SHORTNAME`
- `event_date` — ISO YYYY-MM-DD (or YYYY-MM for foiled plots where only month known)
- `event_year` — int
- `country` — English country name
- `city` — string
- `venue` — specific location
- `venue_type` — enum: `religious_site` | `school` | `university` | `entertainment` | `retail` | `transit` | `public_space` | `residence` | `government` | `workplace` | `healthcare` | `rural` | `multi_site` | `other`
- `perp_name` — string (multiple perps joined with `;`)
- `perp_age` — int (primary perp only)
- `perp_sex` — M | F | trans_MtF | trans_FtM | mixed
- `perp_ethnicity` — string
- `perp_nationality` — string
- `perp_mental_health_flag` — Y | N | Contested
- `status` — C (completed) | PF (partial/failed) | F (foiled pre-attack)
- `fatalities_total_incl_perp` — int
- `fatalities_excl_perp` — int
- `perp_died` — Y | N
- `total_casualties` — int (killed + injured, excl. perp where possible)
- `weapons_primary` — string
- `weapons_secondary` — string (nullable)
- `weapon_modifications` — string (nullable)
- `method_primary` — enum: `firearm` | `vehicle` | `blade` | `arson` | `explosive` | `mixed` | `other`
- `target_description` — string
- `target_type` — enum: `religious` | `ethnic` | `lgbtq` | `women` | `political` | `school_random` | `university_random` | `random_public` | `workplace` | `family` | `police` | `disabled_persons` | `community` | `mixed` | `other`
- `ideology_claimed` — string (what perp said)
- `ideology_assessed` — string (court/academic assessment)
- `ideology_contested` — Y | N
- `subculture_tags` — semicolon list from: `columbine_fandom`, `kolumbayn`, `incel`, `accelerationist`, `great_replacement`, `terrorgram`, `tcc`, `nve`, `groyper`, `soyjak`, `764`, `o9a`, `mku`, `nlm`, `atomwaffen`, `jihadist`, `islamist`, `reichsburger`, `sovereign_citizen`, `ecofascist`, `rwds`, `neo_fascist`, `premillennialist`, `bronycon_farright`, `covid_conspiracist`, `religious_purity`, `separatist`, `misc`
- `manifesto_exists` — Y | N | Partial
- `manifesto_title` — string (nullable)
- `manifesto_length_pages` — int (nullable)
- `manifesto_format` — enum: `text` | `pdf` | `video` | `audio` | `multimodal` | `forum_post` | `letter` | `multi_post_archive`
- `manifesto_language` — string (nullable)
- `manifesto_platform` — string — where originally posted
- `livestream_attempted` — Y | N
- `livestream_successful` — Y | N
- `livestream_platform` — string (nullable)
- `livestream_duration_min` — int (nullable)
- `weapon_inscriptions` — string, verbatim where documented
- `clothing_gear` — string
- `mask_type` — string (nullable)
- `pre_attack_selfies` — string (Y/N + description)
- `music_during_attack` — string (nullable)
- `gamification_elements` — Y | N
- `first_person_camera` — Y | N + type (helmet-cam / GoPro / dashcam / phone)
- `anniversary_attack` — Y | N
- `anniversary_of` — string (what prior attack/date)
- `primary_online_handles` — semicolon list
- `primary_platforms` — semicolon list
- `documented_searches` — string (Google/YouTube/etc. history where in evidence)
- `direct_contact_other_attackers` — string (who + how)
- `named_prior_attackers_incoming` — semicolon list (who perp cited)
- `incoming_citation_count` — int
- `named_by_subsequent_attackers` — semicolon list (who cited perp after)
- `outgoing_citation_count` — int
- `saints_relevance` — low | medium | medium_high | high | very_high | contested
- `saints_tradition` — enum: `core_farright` | `incel` | `kolumbayn` | `columbine_fandom` | `tcc` | `jihadist` | `mixed` | `none`
- `saints_canon_validation_corpus` — Y | N (is this in your dissertation's calibration corpus?)
- `prior_warning_signs` — Y | N
- `how_disrupted` — string (for foiled plots only)
- `sentence` — string
- `cross_references` — semicolon list of datasets (GTD, Mother Jones, Violence Project, ADL, GW, ARC, GNET, Ravndal RTV, Perry/Scrivens, etc.)
- `key_sources` — semicolon list
- `evidence_tier` — 1 (court/coroner/official) | 2 (multi-source reputable journalism) | 3 (tabloid/single-source/contested)
- `audit_flags` — string (explicit flags for contested/retracted/alleged claims)
- `notes` — freeform

---

## 2. Source hierarchy

- **Tier 1**: court documents (indictments, pleas, sentencing memos, coroner findings), government post-incident reports (NY AG, NZ Royal Commission, Saunders Inquiry, Mass Casualty Commission, Federal German BGH/BfV, UK Home Office CONTEST, ASIO, Russian Investigative Committee, Turkish prosecution filings), Europol TE-SAT annual reports, DOJ press releases & affidavits
- **Tier 2**: peer-reviewed academic (Macklin, Ravndal, Perliger, Hoffman, Berger, Schuurman, Kruglova, Malkki, Saarinen), ARC/GNET/GW/CSIS/ADL research publications, long-form investigative journalism (ProPublica/FRONTLINE, Bellingcat, Der Spiegel, Le Monde, Unicorn Riot, Raw Story), coroner inquest transcripts
- **Tier 3**: breaking news, tabloids, single-source claims, pseudonymous researchers, retracted/unverified assertions

---

## 3. Audit corrections (task-brief claims flagged as unsupported)

These claims appeared in the research task briefs but are NOT textually supported in primary sources. Downgrade from "documented citation" to "structural parallel" in the final dataset:

1. **Kato Akihabara 2008 → Minassian Toronto 2018**: Minassian cites Rodger + "4chan Sgt", not Kato. Structural cognate only.
2. **Uematsu Sagamihara 2016 → Tarrant Christchurch 2019**: Tarrant manifesto names Breivik/Roof/Traini/Lundin Pettersson/Lapshyn/Osborne/Bissonnette/Åkerlund. Uematsu is not named. Structural cognate.
3. **Tsushima Odakyu 2021 → Rodger**: Not confirmed in English-language court coverage. Structural parallel.
4. **Hattori Keio Joker 2021 → Holmes Aurora**: Holmes "Joker" attribution is itself a retracted NYPD-relayed rumor. Hattori's costume cites 2019 Phillips/Phoenix *Joker* film, not Holmes directly.
5. **Afanaskina Bryansk 2023 → Hale/Klebold**: Russian investigators determined the "internet diary" was FABRICATED (uploaded after her death). Downgrade to ALLEGED.
6. **Wieambilla Trains 2022 → Waco/Branch Davidian aesthetic**: Bunker confirmed; Waco iconography not found in English primary sources. Need Qld Coroner transcripts.
7. **Kretschmer Winnenden 2009 → Krautchan "Bernd from Bavaria" chat**: Officially retracted by police.
8. **Kimura Kishida 2023 → Yamagami**: Kimura refused to speak with police. Behavioral/thematic parallel only.
9. **Crépol 2023 "on est là pour tuer les Blancs" quote**: Eyewitness only, politically weaponized, not judicially confirmed.

---

## 4. Cases (chronological)

### JPN-2001-IKEDA
- event_date: 2001-06-08
- event_year: 2001
- country: Japan
- city: Ikeda (Osaka Pref.)
- venue: Ikeda Elementary School
- venue_type: school
- perp_name: Mamoru Takuma
- perp_age: 37
- perp_sex: M
- perp_ethnicity: Japanese
- perp_nationality: Japan
- perp_mental_health_flag: Y
- status: C
- fatalities_total_incl_perp: 8
- fatalities_excl_perp: 8
- perp_died: N
- total_casualties: 23
- weapons_primary: deba-bocho kitchen knife (28 cm)
- method_primary: blade
- target_description: young girls at elementary school
- target_type: school_random
- ideology_claimed: none
- ideology_assessed: personal grievance; prior psychiatric history
- saints_relevance: medium
- saints_tradition: none
- sentence: death (executed 14 Sept 2004)
- cross_references: GTD
- key_sources: Japanese court records; Asahi Shimbun
- evidence_tier: 1
- notes: Included as aesthetic-contagion precursor. Akihabara 2008 attack occurred exactly 7 years later to the day; JP commentary treats as anniversary.

### FIN-2007-JOKELA
- event_date: 2007-11-07
- event_year: 2007
- country: Finland
- city: Tuusula
- venue: Jokela High School
- venue_type: school
- perp_name: Pekka-Eric Auvinen
- perp_age: 18
- perp_sex: M
- perp_ethnicity: Finnish
- perp_nationality: Finland
- perp_mental_health_flag: Contested
- status: C
- fatalities_total_incl_perp: 9
- fatalities_excl_perp: 8
- perp_died: Y
- total_casualties: 12
- weapons_primary: SIG Mosquito .22 LR semi-auto
- weapon_modifications: legally purchased; 400+ rounds
- method_primary: firearm
- target_description: classmates and school personnel; principal targeted first
- target_type: school_random
- ideology_claimed: social-Darwinist "natural selection"; anti-humanism
- ideology_assessed: Columbine-replication + nihilist/Nietzschean
- subculture_tags: columbine_fandom
- manifesto_exists: Y
- manifesto_title: "Manifesto of a Natural Selector"
- manifesto_length_pages: 1
- manifesto_format: text + video
- manifesto_language: English
- manifesto_platform: YouTube
- clothing_gear: Sonderkommando Dirlewanger T-shirt (pre-attack photos); "HUMANITY IS OVERRATED" shirt
- pre_attack_selfies: Y; YouTube 'Sturmgeist89' channel, multiple videos incl. "Jokela High School Massacre - 11/7/2007" uploaded hours before attack
- primary_online_handles: Sturmgeist89 (YouTube); NaturalSelector89
- primary_platforms: YouTube; IRC
- named_prior_attackers_incoming: Harris/Klebold (Columbine); Seung-Hui Cho (Virginia Tech 2007)
- incoming_citation_count: 2
- named_by_subsequent_attackers: Saari (Kauhajoki 2008); Marin (Kuopio 2019)
- outgoing_citation_count: 2
- saints_relevance: high
- saints_tradition: columbine_fandom
- sentence: deceased (self-inflicted)
- cross_references: GTD; Violence Project
- key_sources: Finnish Ministry of Justice Jokela investigation report 2009; Saarinen; Malkki
- evidence_tier: 1
- notes: Proto-contagion case for European Columbine fandom. "Natural Selection" T-shirt concept copied from Harris. Transmits Columbine aesthetic into Nordic/CEE space.

### JPN-2008-AKIHABARA
- event_date: 2008-06-08
- event_year: 2008
- country: Japan
- city: Tokyo
- venue: Akihabara pedestrian zone
- venue_type: public_space
- perp_name: Tomohiro Kato
- perp_age: 25
- perp_sex: M
- perp_ethnicity: Japanese
- perp_nationality: Japan
- perp_mental_health_flag: N
- status: C
- fatalities_total_incl_perp: 7
- fatalities_excl_perp: 7
- perp_died: N
- total_casualties: 17
- weapons_primary: rented 5-ton Isuzu Elf truck; Smith & Wesson HRT survival dagger
- method_primary: mixed
- target_description: pedestrians in Akihabara
- target_type: random_public
- ideology_claimed: none; "wanted a girlfriend"; hated winners
- ideology_assessed: proto-incel (himote) / personal grievance
- subculture_tags: incel
- manifesto_exists: Partial
- manifesto_format: text (mobile forum posts)
- manifesto_language: Japanese
- manifesto_platform: Megaview-Net (stc.ne.jp) mobile bulletin board
- anniversary_attack: Y
- anniversary_of: Ikeda Elementary 2001-06-08 (7-year anniversary; widely noted in JP commentary)
- primary_platforms: Megaview-Net mobile BBS
- documented_searches: thousands of posts typed from behind the wheel en route
- saints_relevance: medium
- saints_tradition: incel
- sentence: death (executed 26 July 2022)
- cross_references: GTD
- key_sources: Slater & Galbraith 2011 EJCJS; Ueno Chizuko 2009 "Himote no Misoginii"
- evidence_tier: 1
- audit_flags: Task-brief claim Kato cited textually in Minassian's 2018 Toronto manifesto is NOT confirmed. Minassian cites Rodger + "4chan Sgt". Downgrade to structural parallel.
- notes: Proto-incel contagion origin; pre-Rodger himote index case. No textual downstream citation documented; structural cognate for Toronto 2018.

### FIN-2008-KAUHAJOKI
- event_date: 2008-09-23
- event_year: 2008
- country: Finland
- city: Kauhajoki
- venue: Seinajoki University of Applied Sciences (vocational)
- venue_type: school
- perp_name: Matti Juhani Saari
- perp_age: 22
- perp_sex: M
- perp_ethnicity: Finnish
- perp_nationality: Finland
- perp_mental_health_flag: Y
- status: C
- fatalities_total_incl_perp: 11
- fatalities_excl_perp: 10
- perp_died: Y
- total_casualties: 11
- weapons_primary: Walther P22 pistol
- weapon_modifications: bodies burned with gasoline post-mortem
- method_primary: firearm
- target_description: classmates at vocational school exam hall
- target_type: school_random
- ideology_claimed: misanthropy; hatred of humanity
- ideology_assessed: Columbine/Jokela replication
- subculture_tags: columbine_fandom
- manifesto_exists: Partial
- manifesto_format: video
- manifesto_platform: YouTube
- pre_attack_selfies: Y; YouTube "Wumpscut86" handle; videos captioned "You will die next"
- primary_online_handles: Wumpscut86 (YouTube); Mr Saari (IRC-Galleria)
- primary_platforms: YouTube; IRC-Galleria
- direct_contact_other_attackers: travelled to Jokela to photograph the school before attack (demonstrative pilgrimage)
- named_prior_attackers_incoming: Harris/Klebold; Auvinen (Jokela)
- incoming_citation_count: 2
- named_by_subsequent_attackers: Marin (Kuopio 2019)
- outgoing_citation_count: 1
- saints_relevance: high
- saints_tradition: columbine_fandom
- prior_warning_signs: Y
- sentence: deceased (self-inflicted)
- cross_references: GTD; Violence Project
- key_sources: Finnish MOJ Kauhajoki investigation 2010; Malkki 2014; Lankford 2016
- evidence_tier: 1
- notes: Purchased weapon from same Jokela gun shop as Auvinen. Police searched home 22 May 2008 after anonymous tip but did not revoke permit. Drove 2010 Finnish gun-law tightening.

### DEU-2009-WINNENDEN
- event_date: 2009-03-11
- event_year: 2009
- country: Germany
- city: Winnenden
- venue: Albertville-Realschule + Wendlingen shootout
- venue_type: school
- perp_name: Tim Kretschmer
- perp_age: 17
- perp_sex: M
- perp_ethnicity: German
- perp_nationality: Germany
- perp_mental_health_flag: Y
- status: C
- fatalities_total_incl_perp: 16
- fatalities_excl_perp: 15
- perp_died: Y
- total_casualties: 25
- weapons_primary: Beretta 92FS 9mm (stolen from sport-shooter father)
- method_primary: firearm
- target_description: school students (predominantly female) + random passers-by during escape
- target_type: school_random
- ideology_claimed: none
- ideology_assessed: personal grievance; mental health
- manifesto_exists: N
- clothing_gear: military-style gear
- primary_platforms: Counter-Strike online community
- saints_relevance: medium
- saints_tradition: columbine_fandom
- sentence: deceased (self-inflicted)
- cross_references: GTD; Violence Project; Ravndal RTV
- key_sources: Baden-Württemberg Interior Ministry report 2009
- evidence_tier: 1
- audit_flags: Police initial claim of a Krautchan "Bernd from Bavaria" chat-room announcement the night before was OFFICIALLY RETRACTED. Treat as false.
- notes: Drove 2009 German Weapons Act amendment. Avid Counter-Strike player.

### NOR-2011-BREIVIK
- event_date: 2011-07-22
- event_year: 2011
- country: Norway
- city: Oslo + Utoya Island
- venue: Government quarter (VBIED) + AUF summer camp
- venue_type: government
- perp_name: Anders Behring Breivik
- perp_age: 32
- perp_sex: M
- perp_ethnicity: Norwegian
- perp_nationality: Norway
- perp_mental_health_flag: Contested
- status: C
- fatalities_total_incl_perp: 77
- fatalities_excl_perp: 77
- perp_died: N
- total_casualties: 396
- weapons_primary: VBIED (ANFO ~950 kg); Ruger Mini-14; Glock 17
- weapon_modifications: weapons inscribed with Latin phrases
- method_primary: mixed
- target_description: Norwegian Labour Party / AUF youth camp; "cultural Marxists" as proxy for Muslim immigration
- target_type: political
- ideology_claimed: Knights Templar; counter-jihad; ethno-nationalist; cultural conservative
- ideology_assessed: far-right ethno-nationalist / counter-jihad / Christian-identity framing
- subculture_tags: great_replacement; accelerationist
- manifesto_exists: Y
- manifesto_title: "2083: A European Declaration of Independence"
- manifesto_length_pages: 1518
- manifesto_format: pdf
- manifesto_language: English
- manifesto_platform: emailed to ~1,003 contacts + posted online hours before
- weapon_inscriptions: Latin phrases on rifle
- clothing_gear: pseudo-police uniform on Utoya; fake Knights Templar commendations; Masonic regalia + "compression suit" in staged photos
- pre_attack_selfies: Y; extensively staged self-photography disseminated with manifesto
- primary_platforms: Stormfront; Gates of Vienna; Jihad Watch; document.no; Fjordman blog comments
- named_prior_attackers_incoming: William Pierce Turner Diaries (tangential)
- incoming_citation_count: 1
- named_by_subsequent_attackers: Sonboly (Munich 2016); Bowers; Tarrant (claimed brief contact); Manshaus; Balliet; Gendron; Krajcik; Henderson; Hasson; Mathews-Base; Timofey K (Odintsovo 2025); Kucukyetim (Eskisehir 2024); many others
- outgoing_citation_count: 20
- saints_relevance: very_high
- saints_tradition: core_farright
- saints_canon_validation_corpus: Y
- sentence: 21-year containment (preventive detention); extendable
- cross_references: GTD #201107220008; Europol TE-SAT 2012; Ravndal RTV
- key_sources: 22 July Commission Report (NOU 2012:14); Borchgrevink 2013; Ravndal 2018
- evidence_tier: 1
- notes: Founding saint of modern accelerationist canon. Structural paradigm for manifesto + pre-planning + multi-stage attack.

### USA-2012-AURORA
- event_date: 2012-07-20
- event_year: 2012
- country: USA
- city: Aurora (CO)
- venue: Century 16 theater (Dark Knight Rises premiere)
- venue_type: entertainment
- perp_name: James Holmes
- perp_age: 24
- perp_sex: M
- perp_ethnicity: White
- perp_nationality: USA
- perp_mental_health_flag: Y
- status: C
- fatalities_total_incl_perp: 12
- fatalities_excl_perp: 12
- perp_died: N
- total_casualties: 82
- weapons_primary: Smith & Wesson M&P15 (AR-15); Remington 870; Glock 22
- weapon_modifications: tear-gas grenades; booby-trapped apartment
- method_primary: firearm
- target_description: moviegoers at midnight premiere (random)
- target_type: random_public
- ideology_claimed: none
- ideology_assessed: psychotic break; schizophrenia diagnosed post-arrest
- manifesto_exists: Partial
- manifesto_title: notebook mailed to UC psychiatrist Lynne Fenton
- manifesto_format: handwritten notebook with drawings
- manifesto_platform: postal mail (undelivered pre-attack)
- clothing_gear: tactical gear; ballistic helmet; gas mask; body armor
- mask_type: gas mask
- pre_attack_selfies: selfies with weapons + orange hair posted to Adult Friend Finder profile pre-attack
- primary_platforms: Adult Friend Finder; Match.com; online gaming
- saints_relevance: low
- saints_tradition: none
- sentence: 12 consecutive life sentences + 3318 years
- cross_references: GTD; Mother Jones; Violence Project #146
- key_sources: Court records CR2012-1522; Fenton/Rocky Mountain PBS investigation
- evidence_tier: 1
- audit_flags: NYPD-originated "Joker" claim later retracted; Holmes denied Joker emulation. The Dark Knight Rises villain was Bane, not the Joker.
- notes: Important null case for ideological framework; aesthetic "Joker" attribution retracted. Apartment booby-trap precedent.

### USA-2012-OAKCREEK
- event_date: 2012-08-05
- event_year: 2012
- country: USA
- city: Oak Creek (WI)
- venue: Sikh Temple of Wisconsin
- venue_type: religious_site
- perp_name: Wade Michael Page
- perp_age: 40
- perp_sex: M
- perp_ethnicity: White
- perp_nationality: USA
- perp_mental_health_flag: N
- status: C
- fatalities_total_incl_perp: 7
- fatalities_excl_perp: 6
- perp_died: Y
- total_casualties: 11
- weapons_primary: Springfield XD 9mm
- method_primary: firearm
- target_description: Sikh worshippers (likely misidentified as Muslim)
- target_type: religious
- ideology_claimed: implicit via band affiliations
- ideology_assessed: white-supremacist; Hammerskin Nation
- subculture_tags: accelerationist; great_replacement
- manifesto_exists: N
- clothing_gear: Celtic cross "38" tattoo; 14-words imagery
- pre_attack_selfies: Y; extensive tattoos documented
- primary_platforms: Stormfront (registered); Hammerskin Nation network
- named_by_subsequent_attackers: referenced in some Terrorgram materials
- outgoing_citation_count: 1
- saints_relevance: medium_high
- saints_tradition: core_farright
- sentence: deceased (self-inflicted)
- cross_references: GTD #201208050001; ADL; SPLC
- key_sources: FBI post-incident; ADL backgrounder; SPLC Intelligence Report Fall 2012
- evidence_tier: 1
- notes: Hatecore/neo-Nazi music scene pipeline. Canonized in Hammerskin circles.

### USA-2012-SANDYHOOK
- event_date: 2012-12-14
- event_year: 2012
- country: USA
- city: Newtown (CT)
- venue: Sandy Hook Elementary + maternal home
- venue_type: school
- perp_name: Adam Lanza
- perp_age: 20
- perp_sex: M
- perp_ethnicity: White
- perp_nationality: USA
- perp_mental_health_flag: Y
- status: C
- fatalities_total_incl_perp: 28
- fatalities_excl_perp: 27
- perp_died: Y
- total_casualties: 30
- weapons_primary: Bushmaster XM15-E2S; Glock 20SF; SIG P226
- method_primary: firearm
- target_description: 1st-grade students + school staff; mother killed first at home
- target_type: school_random
- ideology_claimed: none
- ideology_assessed: severe mental illness + fixation on Columbine / mass-shooter catalog
- subculture_tags: columbine_fandom
- manifesto_exists: Partial
- manifesto_title: spreadsheet catalog of prior mass murderers
- manifesto_format: digital spreadsheet + forum posts
- manifesto_platform: hard drives recovered from home
- clothing_gear: black fatigues; earplugs
- primary_online_handles: "Kaynbred"; "Smiggles"
- primary_platforms: shockedbeyondbelief.com forum (school-shooter fandom); 4chan /r9k/ (alleged); Encyclopedia Dramatica
- documented_searches: extensive Google/YouTube research on Columbine, Virginia Tech, Akihabara Tomohiro Kato, Anders Breivik, Dawson College shooter Kimveer Gill; spreadsheet catalog of ~500 mass murderers
- named_prior_attackers_incoming: Harris/Klebold; Cho; Kimveer Gill; Tomohiro Kato; Breivik (all catalogued)
- incoming_citation_count: 5
- named_by_subsequent_attackers: Hale (Covenant 2023); Rupnow (Madison 2024); many TCC/Columbiner fandom references
- outgoing_citation_count: 2
- saints_relevance: very_high
- saints_tradition: columbine_fandom
- saints_canon_validation_corpus: Y
- sentence: deceased (self-inflicted)
- cross_references: GTD #201212140018; Violence Project #153; Mother Jones
- key_sources: CT State's Attorney Sedensky Report Nov 2013; Peter Lanza/Andrew Solomon New Yorker 2014; OCA report 2014
- evidence_tier: 1
- notes: Paradigm case for documented pre-attack digital research. Cataloged Kato explicitly — direct JP→US contagion link at the consumption level. Central node of Columbine fandom / TCC.

### USA-2014-ISLAVISTA
- event_date: 2014-05-23
- event_year: 2014
- country: USA
- city: Isla Vista (CA)
- venue: UCSB area (apartment, sorority, deli)
- venue_type: public_space
- perp_name: Elliot Rodger
- perp_age: 22
- perp_sex: M
- perp_ethnicity: Mixed (White/Malaysian Chinese)
- perp_nationality: UK/USA
- perp_mental_health_flag: Y
- status: C
- fatalities_total_incl_perp: 7
- fatalities_excl_perp: 6
- perp_died: Y
- total_casualties: 21
- weapons_primary: SIG P226; Glock 34; SIG P224; knife; BMW as vehicle weapon
- method_primary: mixed
- target_description: sorority women ("hot blondes"); Alpha Phi house targeted
- target_type: women
- ideology_claimed: retribution against women
- ideology_assessed: founding incel/misogynist/male-supremacist terror act
- subculture_tags: incel
- manifesto_exists: Y
- manifesto_title: "My Twisted World"
- manifesto_length_pages: 107
- manifesto_format: multimodal (PDF + YouTube "Retribution" video)
- manifesto_language: English
- manifesto_platform: emailed to ~30 contacts + posted online + YouTube
- clothing_gear: Ray-Ban Aviator sunglasses (signature); Hugo Boss style; BMW 328i coupe as status prop
- pre_attack_selfies: Y; extensive YouTube vlogging channel "ElliotRodger" with 20+ videos pre-attack
- primary_online_handles: ElliotRodger (YouTube); various PUAHate, bodybuilding.com misc handles
- primary_platforms: PUAHate.com; ForeverAlone; bodybuilding.com "misc"
- named_by_subsequent_attackers: Minassian (Toronto 2018); Davison (Plymouth 2021); Long (Atlanta 2021); Hattori (Keio 2021, structural); Garcia (Allen 2023); Lex Ashton (CCH Sur 2025); numerous foiled plotters
- outgoing_citation_count: 8
- saints_relevance: very_high
- saints_tradition: incel
- saints_canon_validation_corpus: Y
- sentence: deceased (self-inflicted)
- cross_references: GTD #201405230002; Violence Project #162; ADL incel backgrounder
- key_sources: Santa Barbara Sheriff Report Feb 2015; Hoffman, Ware & Shapiro 2020 SCT
- evidence_tier: 1
- notes: Paradigm case for incel canon. "Saint Elliot" / "Supreme Gentleman". YouTube video retroactively treated as proto-livestream.

### DNK-2015-COPENHAGEN
- event_date: 2015-02-14
- event_year: 2015
- country: Denmark
- city: Copenhagen
- venue: Krudttoenden cafe + Great Synagogue
- venue_type: entertainment
- perp_name: Omar Abdel Hamid El-Hussein
- perp_age: 22
- perp_sex: M
- perp_ethnicity: Palestinian-Jordanian
- perp_nationality: Denmark
- status: C
- fatalities_total_incl_perp: 3
- fatalities_excl_perp: 2
- perp_died: Y
- total_casualties: 8
- weapons_primary: M95 military rifle (stolen); CZ pistol
- method_primary: firearm
- target_description: free-speech seminar (Lars Vilks present); Jewish worshippers at synagogue
- target_type: religious
- ideology_claimed: ISIS
- ideology_assessed: ISIS-inspired; rapid self-radicalization in prison
- subculture_tags: jihadist; islamist
- manifesto_exists: Partial
- manifesto_format: forum_post
- manifesto_platform: Facebook
- pre_attack_selfies: fake-Airbnb reconnaissance
- primary_platforms: Facebook
- saints_relevance: low
- saints_tradition: jihadist
- sentence: deceased (police shootout)
- cross_references: GTD; Europol TE-SAT 2016
- evidence_tier: 1
- notes: Cited by Esbensen (Copenhagen Field's 2022) as structural model indirectly (Esbensen cited Randy Stair instead).

### FRA-2015-HEBDO
- event_date: 2015-01-07
- event_year: 2015
- country: France
- city: Paris
- venue: Charlie Hebdo offices + Porte de Vincennes + Montrouge
- venue_type: workplace
- perp_name: Said Kouachi; Cherif Kouachi; Amedy Coulibaly
- perp_age: 34
- perp_sex: M
- perp_ethnicity: French-Algerian; French-Malian
- perp_nationality: France
- status: C
- fatalities_total_incl_perp: 20
- fatalities_excl_perp: 17
- perp_died: Y
- total_casualties: 39
- weapons_primary: AK-pattern rifles; handguns; shotgun
- method_primary: firearm
- target_description: Hebdo journalists; Jewish shoppers; police
- target_type: mixed
- ideology_claimed: AQAP (Kouachis); ISIS (Coulibaly)
- ideology_assessed: jihadist
- subculture_tags: jihadist; islamist
- manifesto_exists: Partial
- manifesto_format: video
- clothing_gear: paramilitary dress
- primary_platforms: Buttes-Chaumont cell (pre-social-media)
- saints_relevance: low
- saints_tradition: jihadist
- cross_references: GTD; Europol TE-SAT 2016; CSIS
- key_sources: French parliamentary inquiry reports
- evidence_tier: 1

### USA-2015-CHARLESTON
- event_date: 2015-06-17
- event_year: 2015
- country: USA
- city: Charleston (SC)
- venue: Emanuel AME Church
- venue_type: religious_site
- perp_name: Dylann Roof
- perp_age: 21
- perp_sex: M
- perp_ethnicity: White
- perp_nationality: USA
- perp_mental_health_flag: N
- status: C
- fatalities_total_incl_perp: 9
- fatalities_excl_perp: 9
- perp_died: N
- total_casualties: 10
- weapons_primary: Glock 41 .45
- method_primary: firearm
- target_description: Black worshippers at Bible study
- target_type: ethnic
- ideology_claimed: white-supremacist racial war
- ideology_assessed: confirmed
- subculture_tags: accelerationist; great_replacement
- manifesto_exists: Y
- manifesto_title: "The Last Rhodesian"
- manifesto_format: text + photo essay
- manifesto_language: English
- manifesto_platform: lastrhodesian.com (personal website)
- clothing_gear: Rhodesian / apartheid-era SA flag patches on jacket
- pre_attack_selfies: Y; extensive; Confederate-flag poses; burning US flag; lit-match photos
- documented_searches: "black on white crime" (first CofCC exposure, documented in manifesto)
- primary_platforms: Council of Conservative Citizens website; Stormfront-adjacent
- named_by_subsequent_attackers: Earnest; Crusius; Gendron; Krajcik; Henderson; Garcia (Allen); Palmeter (Jacksonville); Timofey K (Odintsovo)
- outgoing_citation_count: 8
- saints_relevance: very_high
- saints_tradition: core_farright
- saints_canon_validation_corpus: Y
- sentence: federal death + state 9 life sentences
- cross_references: GTD #201506170000; New America; ADL
- key_sources: FBI 302s; DOJ sentencing memo; Bell 2018
- evidence_tier: 1
- notes: Primary triumvirate member (Breivik-Roof-Tarrant).

### SWE-2015-TROLLHATTAN
- event_date: 2015-10-22
- event_year: 2015
- country: Sweden
- city: Trollhattan
- venue: Kronan school
- venue_type: school
- perp_name: Anton Lundin Pettersson
- perp_age: 21
- perp_sex: M
- perp_ethnicity: Swedish
- perp_nationality: Sweden
- perp_mental_health_flag: Contested
- status: C
- fatalities_total_incl_perp: 4
- fatalities_excl_perp: 3
- perp_died: Y
- total_casualties: 4
- weapons_primary: sword (historical reproduction); unused tanto; Molotov (unused)
- method_primary: blade
- target_description: predominantly immigrant students at multicultural school; CCTV showed he spared white-skinned students
- target_type: ethnic
- ideology_claimed: none explicit
- ideology_assessed: neo-Nazi ethno-nationalist (assessed post-mortem)
- subculture_tags: great_replacement; accelerationist
- manifesto_exists: N
- clothing_gear: black cape; Stahlhelm-style helmet; paintball mask; all-black theatrical ensemble
- mask_type: paintball mask
- music_during_attack: Rob Zombie "Dragula" played on loop in car and during attack
- pre_attack_selfies: staged "headshot" photo with classmates before attack
- primary_platforms: Facebook; Stormfront (limited)
- named_by_subsequent_attackers: Tarrant (explicit — name inscribed on Christchurch firearms); Gendron (Buffalo manifesto); Hugo Jackson's mask
- outgoing_citation_count: 3
- saints_relevance: very_high
- saints_tradition: core_farright
- sentence: deceased (police shooting)
- cross_references: GTD; Ravndal RTV
- key_sources: Swedish police Pilot report; Ranstorp ICCT
- evidence_tier: 1
- notes: Central aesthetic-contagion reference — highest-frequency "saint" citation in NZ/US/European subset. Direct theatrical/medieval aesthetic replicated later.

### AUT-2015-GRAZ-SUV
- event_date: 2015-06-20
- event_year: 2015
- country: Austria
- city: Graz
- venue: pedestrianized Herrengasse street
- venue_type: public_space
- perp_name: Alen Rizvanovic
- perp_age: 26
- perp_sex: M
- perp_ethnicity: Bosnian-Austrian
- perp_nationality: Austria
- status: C
- fatalities_total_incl_perp: 3
- fatalities_excl_perp: 3
- perp_died: N
- total_casualties: 38
- weapons_primary: green Daewoo Rexton SUV + kitchen knife
- method_primary: vehicle
- target_description: pedestrians in city center
- target_type: random_public
- ideology_claimed: none (silent)
- ideology_assessed: psychotic/personal crisis
- primary_platforms: Twitter (>2,500 followers; deleted all tweets and messages before attack except one)
- sentence: life (no parole); died by suicide in Stein Correctional solitary cell 23 Sept 2023
- cross_references: GTD; Europol TE-SAT 2016
- evidence_tier: 1
- notes: Under domestic-violence restraining order with firearms confiscated at time of attack. Distinctive: deleted social-media trail pre-attack.

### FRA-2015-BATACLAN
- event_date: 2015-11-13
- event_year: 2015
- country: France
- city: Paris
- venue: Bataclan + Stade de France + cafes
- venue_type: entertainment
- perp_name: 9-man ISIS cell (Abaaoud directed)
- perp_sex: M
- perp_ethnicity: Mixed French-Belgian-Moroccan
- perp_nationality: France/Belgium
- status: C
- fatalities_total_incl_perp: 137
- fatalities_excl_perp: 130
- perp_died: Y
- total_casualties: 548
- weapons_primary: AK-47s; TATP suicide vests
- method_primary: mixed
- target_description: concertgoers; soccer match; diners
- target_type: random_public
- ideology_claimed: ISIS
- ideology_assessed: confirmed ISIS external operation
- subculture_tags: jihadist; islamist
- manifesto_exists: Partial
- manifesto_format: ISIS Dabiq magazine + communiques
- clothing_gear: suicide vests; tactical dress
- primary_platforms: encrypted Telegram; ISIS Dabiq
- saints_relevance: low
- saints_tradition: jihadist
- cross_references: GTD; Europol TE-SAT 2016; CSIS
- key_sources: Fenech-Pietrasanta Rapport
- evidence_tier: 1

### USA-2015-SANBERN
- event_date: 2015-12-02
- event_year: 2015
- country: USA
- city: San Bernardino (CA)
- venue: Inland Regional Center
- venue_type: workplace
- perp_name: Syed Rizwan Farook; Tashfeen Malik
- perp_age: 28
- perp_sex: mixed
- perp_ethnicity: Pakistani American; Pakistani
- perp_nationality: USA; Pakistan
- status: C
- fatalities_total_incl_perp: 16
- fatalities_excl_perp: 14
- perp_died: Y
- total_casualties: 38
- weapons_primary: DPMS A-15; Smith & Wesson M&P15; pistols
- method_primary: firearm
- target_description: county health workers holiday party
- target_type: workplace
- ideology_claimed: ISIS (Malik posted bayah mid-attack)
- ideology_assessed: jihadist-inspired
- subculture_tags: jihadist
- manifesto_exists: Partial
- manifesto_format: forum_post
- manifesto_platform: Facebook
- primary_platforms: Facebook (private); encrypted messaging
- saints_relevance: low
- saints_tradition: jihadist
- cross_references: GTD; New America; FBI
- key_sources: FBI post-incident; House Homeland Security report
- evidence_tier: 1
