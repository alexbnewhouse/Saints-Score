# Saints Score Pipeline — Build Specification

**Owner:** Alex (CU Boulder, Political Science)
**Agent role:** Opus 4.6 coding agent, operating in *copilot* mode — generate code, surface intermediate outputs for review, and flag methodological decisions rather than silently resolve them.
**Dissertation chapter:** Saints Score (computational political religion, Ch. 3).

OPERATIONAL NOTES: **Always use green team-red team-refactor team processes; always check your work; always push to remote when finished**.

---

## 1. Project Overview

This project operationalizes a quantitative instrument — the **Saints Score** — for measuring the degree to which online communities canonize perpetrators of mass-casualty violence. The empirical context is /pol/ on 4chan, 2010–2021. The theoretical frame is **computational political religion (CPR)**: the claim that certain online extremist milieus exhibit religion-like processes (martyrdom, hagiography, liturgical repetition) whose structure can be measured in text data.

The scientific contribution is threefold:

1. A reusable instrument for quantifying attacker canonization, suitable for threat assessment applications (including pitching to NIJ).
2. An empirical test of which attack characteristics predict canonization.
3. A methodological demonstration that transformer-based, dictionary-free measurement is tractable for adversarial online text.

### 1.1 Research questions

- **RQ1 (measurement):** Can the Saints Score be reliably computed from observational text data, and does it converge with qualitative judgments of canonization (e.g., Breivik, Tarrant, Roof all score high; unsuccessful / ideologically illegible attackers score low)?
- **RQ2 (variance):** Which attack-level characteristics — ideology, weapon, manifesto presence, livestream, target type, casualty count, perpetrator demography — predict Saints Score variance?
- **RQ3 (component structure):** Do the Saints Score subcomponents (affective valence, intensity, longevity, linguistic convergence) load on a single latent construct, or are they dissociable dimensions of canonization?

### 1.2 Hypotheses

- **H1:** Manifesto + livestream attackers score significantly higher than attackers without either.
- **H2:** Attacks targeting out-groups salient to /pol/'s dominant ideology (racial/religious minorities, left-coded targets) score higher than attacks targeting in-group-coded targets, controlling for casualty count.
- **H3:** The four subcomponents load on a single latent factor with reliability ω ≥ 0.7, supporting a unidimensional canonization construct.

---

## 2. Data Specifications

### 2.1 Attack case dataset

- **Path:** `data/raw/cases_audited.csv`
- **Unit of observation:** one attempted or successful mass-casualty attack in an OECD country, July 2011 (Breivik) through 2021 (cutoff imposed by /pol/ dump).
- **Expected fields:** perpetrator name(s) and aliases, date, country, weapon, casualties (killed/wounded), target type, ideology, manifesto (y/n, URL/text if available), livestream (y/n), prior online presence, and a rich set of aesthetic/characteristic metadata.
- **Agent task:** load, validate schema with Pandera, and produce a cleaning report. Flag any attacks missing required fields (date, perpetrator name, at least one alias).

### 2.2 /pol/ corpus

- **Path:** `data/raw/pol.csv.tar.gz`
- **Source:** 4plebs archival dump; approximate coverage 2010-01 through 2021-12. Text posts only.
- **Size:** large — expect tens of GB uncompressed, low-to-mid hundreds of millions of posts.
- **Agent task:** stream-parse to partitioned Parquet (`data/interim/pol/year=YYYY/month=MM/*.parquet`) using Polars. Do **not** load the full corpus into memory. Validate row counts against the source CSV manifest and log per-month coverage gaps.

Required Parquet columns (post-processing):

| column | type | notes |
|---|---|---|
| `post_id` | i64 | globally unique |
| `thread_id` | i64 | |
| `board` | str | always `pol` here |
| `timestamp_utc` | datetime[us] | parsed from 4plebs unix ts |
| `poster_id` | str | ephemeral, per-thread |
| `title` | str | subject line, often null |
| `body` | str | post text, HTML stripped |
| `body_clean` | str | additional normalization for modeling (see §6.1) |
| `reply_to` | list[i64] | extracted from `>>NNN` tokens |
| `has_image` | bool | |
| `country_code` | str | flag-derived if available |

### 2.3 Storage conventions

- All intermediate and processed data: **Parquet with zstd compression**.
- All dataframe ops: **Polars** (lazy where possible). No pandas in the main pipeline; pandas is acceptable only as a glue layer for libraries that require it (e.g., PyMC posterior I/O).

---

## 3. Computational Environment

Two machines are available. Route work accordingly.

- **Framework Desktop** — AMD Ryzen AI MAX+ 395, 128 GB unified RAM, Fedora 43. Primary platform for data ingest, Polars pipelines, Ollama-served local LLMs (Vulkan backend), and embedding inference at scale (large batches fit in unified memory).
- **RTX 5080 workstation** — CUDA. Use for transformer training/fine-tuning and any job that benefits from dedicated VRAM more than from unified-memory capacity.

### 3.1 Stack

- **Python:** 3.12+, managed with `uv`. Lock with `uv.lock`, pin to a single resolved environment.
- **Core:** `polars`, `pyarrow`, `pydantic`, `pandera[polars]`, `click`, `loguru`.
- **NLP / ML:** `transformers`, `sentence-transformers`, `torch` (CUDA on 5080; CPU fallback elsewhere), `accelerate`, `vllm` (5080 only; optional), `llama-cpp-python` or direct Ollama HTTP calls on Framework Desktop.
- **Stats:** `pymc`, `arviz`, `bambi` (optional, for regression convenience), `scipy`, `numpy`.
- **Viz:** `matplotlib`, `plotnine`, `seaborn` as needed. No plotly unless the agent has a reason.
- **Testing/quality:** `pytest`, `pytest-cov`, `hypothesis`, `ruff`, `mypy` (strict on core modules), `pre-commit`.

### 3.2 Config and secrets

- All paths, model IDs, window widths, seeds live in `src/saints_score/config.py` as a Pydantic `Settings` model, overridable via env vars and a `config.toml`.
- `SEED = 20260414` (prospectus date — for luck and reproducibility).
- No secrets expected. If any (e.g., HF token for gated models), use `.env` loaded via `pydantic-settings`, never committed.

---

## 4. Project Structure

```
saints-score/
├── README.md
├── SAINTS_SCORE_SPEC.md          # this document
├── pyproject.toml
├── uv.lock
├── .python-version
├── .pre-commit-config.yaml
├── Makefile                      # common entry points
├── config.toml
├── data/
│   ├── raw/                      # cases_audited.csv, pol.csv.tar.gz
│   ├── interim/                  # parsed parquet shards
│   └── processed/                # per-attack windows, features, scores
├── src/saints_score/
│   ├── __init__.py
│   ├── config.py
│   ├── logging.py
│   ├── io/                       # parquet readers/writers, tar streaming
│   ├── ingest/                   # pol.csv.tar.gz → parquet
│   ├── cases/                    # case dataset loading + validation
│   ├── mentions/                 # attacker mention detection (§6.2)
│   ├── affect/                   # sentiment + emotion (§6.3)
│   ├── temporal/                 # intensity, longevity (§6.4)
│   ├── semantic/                 # embeddings + convergence (§6.5)
│   ├── scoring/                  # composite Saints Score (§6.6)
│   ├── models/                   # PyMC regressions (§6.7)
│   └── viz/                      # shared plotting utilities
├── scripts/                      # CLI entry points per phase
│   ├── 01_ingest_pol.py
│   ├── 02_detect_mentions.py
│   ├── 03_score_affect.py
│   ├── 04_compute_temporal.py
│   ├── 05_compute_semantic.py
│   ├── 06_assemble_saints_score.py
│   └── 07_fit_attack_regression.py
├── notebooks/                    # exploratory only; not in pipeline
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/                 # tiny sampled data
├── out/
│   ├── figures/
│   ├── tables/
│   └── scores/
└── docs/
    ├── codebook.md               # variable definitions
    ├── mention_detection.md      # writeup of detection protocol
    └── decisions.md              # running log of methodological choices
```

Every CLI script should accept `--config`, `--dry-run`, `--limit N` (for smoke testing), and produce a structured run log in `out/runs/<timestamp>/`.

---

## 5. Methodological Principles

- **Transformer-first.** Dictionary and regex methods are permitted only as candidate-generation steps feeding a transformer classifier, never as final adjudicators. /pol/ users adversarially evolve spellings; static lexicons silently degrade over time.
- **Copilot not autopilot.** For every phase, produce intermediate artifacts (confusion matrices, sampled positive/negative examples, distribution plots) that Alex can inspect before the next phase is run.
- **Replication discipline.** Every numerical result traceable to a seed, a config hash, a code commit, and an input data hash. See §7.
- **Validation before scale.** Every new classifier is validated on a hand-coded sample (n ≥ 200 per attacker, stratified) before being run over the full corpus. Hand-coding can be done by the agent flagging candidates for Alex to adjudicate in a simple TUI or CSV loop.
- **No PII beyond what is already public.** Attacker names are public record. Do not extract or store ephemeral personal information about non-attacker posters beyond what is already in the 4plebs dump.

---

## 6. Pipeline Phases

Each phase has: **inputs**, **outputs**, **method**, **acceptance criteria**. The agent must halt at the end of each phase, produce a run summary, and wait for Alex's go/no-go before continuing.

### 6.1 Phase 1 — Ingest and normalize /pol/

**Inputs:** `data/raw/pol.csv.tar.gz`, `data/raw/cases_audited.csv`.

**Method:**
- Stream-decompress the tar.gz; iterate CSV rows in chunks of ~1M rows.
- Parse timestamps, strip HTML, extract reply graph (`>>NNN`), normalize unicode (NFKC), lowercase a *secondary* `body_clean` column (keep raw `body` intact for audit). Do **not** stem or lemmatize.
- Write partitioned Parquet keyed on `(year, month)`.
- Compute and persist a corpus manifest: per-month post counts, unique thread counts, mean/median post length, byte sizes, content hashes of each Parquet file.

**Outputs:**
- `data/interim/pol/year=YYYY/month=MM/part-*.parquet`
- `data/interim/pol_manifest.json`
- `data/processed/cases.parquet` (validated case dataset)

**Acceptance criteria:**
- Row count within 1% of source CSV line count (minus header).
- No month in 2010-01 through 2021-12 with zero posts unless 4plebs itself is gapped; log all gaps.
- Round-trip test: sample 1k random posts, reconstruct original text, confirm match.

### 6.2 Phase 2 — Attacker mention detection

This is the hardest phase. Do not treat it as string-matching.

**Inputs:** case dataset, ingested /pol/ corpus.

**Method (multi-stage weak supervision):**

1. **Seed alias inventory.** For each attacker, assemble a seed list from: canonical name, news-reported aliases, Wikipedia redirects, KnowYourMeme entries (when present). Store in `data/processed/aliases_seed.parquet` with `source` attribution.
2. **Candidate retrieval — lexical.** For each seed alias, retrieve posts by (a) exact substring, (b) `rapidfuzz` ratio ≥ 85 on tokens of length ≥ 4, (c) soundex-like phonetic match as a recall-boost. Over-retrieve; precision is handled downstream.
3. **Candidate retrieval — semantic.** For each attacker, construct short natural-language probes (e.g., "a post referring to the 2019 Christchurch mosque shooter"). Embed posts with `BAAI/bge-large-en-v1.5` or `nomic-embed-text-v1.5` (decision: §8). Retrieve top-k nearest neighbors per probe per attacker. Index with `usearch` or FAISS; do not store the full dense matrix longer than needed.
4. **LLM adjudication.** For each candidate, classify with a local LLM (via Ollama: Qwen 2.5 32B or Llama 3.3 70B, whichever fits with acceptable throughput on the Framework Desktop) using a structured few-shot prompt: `{post_text, attacker_name, attacker_context}` → `{is_reference: bool, confidence: float, inferred_alias: str|null, is_oblique: bool}`. Cache all LLM outputs (key: hash of prompt + model + version).
5. **Alias bootstrapping.** From posts adjudicated positive, extract high-TF-IDF tokens and short n-grams that co-occur disproportionately with the attacker relative to a random /pol/ baseline. Human-review (Alex) the top candidates; promote survivors to the alias inventory. Iterate stages 2–5 up to three rounds or until no new aliases survive review.
6. **Oblique-reference handling.** Flag posts that the LLM classifies as `is_oblique=True` (e.g., "subscribe to PewDiePie," "Knights Templar" in Breivik's case, "disco tier" for Crusius). Maintain a separate table of oblique reference patterns per attacker with provenance.

**Validation:** Alex hand-codes a stratified sample of 200 posts per attacker (balanced positive/negative predicted). Report precision, recall, F1, and a breakdown by `is_oblique`. **Target precision ≥ 0.90, recall ≥ 0.75** at the final threshold; if not met, do not proceed to Phase 3.

**Outputs:**
- `data/processed/mentions.parquet`: `(post_id, attacker_id, confidence, is_oblique, alias_matched, source_stage)`.
- `data/processed/aliases_final.parquet`.
- `out/tables/mention_detection_eval.csv`.
- `docs/mention_detection.md` with worked examples.

### 6.3 Phase 3 — Affective classification

**Inputs:** `mentions.parquet`, post text.

**Method:**
- **Sentiment:** `cardiffnlp/twitter-xlm-roberta-base-sentiment` (3-way). Validated on social-media text; reasonable prior.
- **Emotion:** `SamLowe/roberta-base-go_emotions` (27 emotions + neutral, multilabel). This is the most comprehensive open-weights emotion model; /pol/-relevant targets (anticipation, joy, admiration, gloating/excitement, anger, disappointment, envy) are covered.
- **Toxicity-aware second pass:** `unitary/unbiased-toxic-roberta` as a control covariate, *not* as a filter. Toxicity and sentiment are correlated on /pol/; we want both signals.
- Run in fp16 on RTX 5080, batch size tuned to VRAM. Cache scores keyed on `(post_id, model_id, model_revision)` in Parquet.

**Domain-validity check:** hand-code 300 posts for sentiment and 300 for emotion. Report Krippendorff's α between model and human. If α < 0.5 on either, flag for potential fine-tuning (defer fine-tuning decision to Alex).

**Outputs:**
- `data/processed/affect_scores.parquet`
- `out/tables/affect_validation.csv`

### 6.4 Phase 4 — Temporal metrics

**Inputs:** `mentions.parquet`, case dates.

**Definitions (operationalized):**

- Let $t=0$ be the UTC timestamp of attack $a$. Define windows:
  - *Baseline:* $[t-365d, t-1d]$
  - *Immediate:* $[t, t+7d]$
  - *Near-term:* $[t+8d, t+90d]$
  - *Long-term:* $[t+91d, t+730d]$

- **Intensity** ($I_a$): proportion of /pol/ posts mentioning attacker $a$ during the immediate window, normalized by total /pol/ posting volume in that window:
  $$I_a = \frac{\text{mentions}_a^{[t, t+7d]}}{\text{total posts}^{[t, t+7d]}}$$

- **Longevity** ($L_a$): fit a power-law decay $m(\tau) = C \tau^{-\alpha}$ to daily mention counts for $\tau \in [1, 730]$ days post-attack, after subtracting the baseline rate. $L_a = 1/\alpha_a$ (higher = slower decay = stickier). Use robust regression; report fit diagnostics per attacker.

- Persist daily mention counts, baseline rate, fitted $\alpha$, and standard error.

**Outputs:**
- `data/processed/temporal_metrics.parquet`
- `out/figures/decay_per_attacker/*.png`

### 6.5 Phase 5 — Semantic convergence

**Inputs:** mention-set posts per attacker.

**Method:**
- Embed each post in the attacker's mention set using the same model as §6.2 (consistency).
- **Similarity** ($S_a$): compute pairwise cosine similarity across a random sample of up to 10,000 posts per attacker; report the median, IQR, and distribution. Higher median = tighter discursive convergence = more liturgical/memetic repetition.
- Complement with a **topic concentration** measure: cluster embeddings (HDBSCAN), report the proportion of posts in the top-3 clusters as a robustness check.
- Optionally fit a per-attacker unigram entropy over content tokens as a non-embedding baseline.

**Outputs:**
- `data/processed/semantic_metrics.parquet`
- `out/figures/similarity_distributions/*.png`

### 6.6 Phase 6 — Composite Saints Score

The informal equation is:

$$\text{Saints}_a = \frac{E^+_a}{E^-_a} \cdot (I_a + L_a + \tilde{S}_a)$$

This has known issues: the ratio is unbounded, the sum mixes unit-heterogeneous terms, and nothing handles measurement uncertainty. The agent will compute **two** versions side by side:

1. **Naïve version.** As specified, after per-term min-max scaling of $I$, $L$, $\tilde{S}$ to $[0,1]$, and replacing the raw ratio with $\log((E^+ + \epsilon)/(E^- + \epsilon))$ z-scored across attackers. Produces a single scalar per attacker.

2. **Principled version — Bayesian measurement model.** Treat Saints Score as a latent variable $\eta_a$ with five continuous indicators: $\log(E^+/E^-)$, $I_a$, $L_a$, $\tilde{S}_a$, and mention volume (log). Fit a one-factor confirmatory model in PyMC with weakly-informative priors on loadings and residual variances. Report factor scores (posterior means + 89% HDIs), loading estimates, and model-level diagnostics (PPC, LOO). This version gives Alex an uncertainty-aware Saints Score suitable for downstream inference.

**Outputs:**
- `out/scores/saints_naive.csv`
- `out/scores/saints_bayes.csv` (with `mean`, `hdi_lo`, `hdi_hi`)
- `out/figures/saints_score_comparison.png` (naïve vs Bayes)
- `docs/scoring.md`

### 6.7 Phase 7 — Attack-characteristic regression

**Inputs:** Saints scores (Bayesian), case metadata.

**Method:**
- Hierarchical Bayesian regression in PyMC. DV: posterior-mean Saints Score (or, preferred, propagate uncertainty by refitting on posterior draws).
- IVs: ideology (categorical), weapon type, manifesto (bool), livestream (bool), target type, log(casualties), attacker demographics, country, year.
- Partial pooling on ideology and country.
- Weakly informative priors (Normal(0, 1) on standardized coefficients; HalfNormal on scales).
- Report: coefficient tables with HDIs, posterior predictive checks, LOO, and contrast plots for the key H1 and H2 tests.

**Outputs:**
- `out/tables/regression_coefficients.csv`
- `out/figures/regression_forest.png`, `out/figures/ppc.png`
- `out/models/attack_regression.nc` (ArviZ InferenceData)

---

## 7. Replication and Reproducibility Standards

Target audience: computational social scientists who will want to rerun this.

- **Environment.** `pyproject.toml` + `uv.lock`. A `make env` target reproduces the environment byte-for-byte on Linux.
- **Data hashes.** SHA-256 of every raw input file, stored in `data/raw/MANIFEST.sha256`. Every pipeline stage records the hashes of its inputs in its run log.
- **Seeds.** Single `SEED` constant propagated everywhere (`numpy`, `torch`, `random`, `pymc`).
- **Model versions.** All Hugging Face model IDs pinned with revision hashes, not tags.
- **Run logs.** Each CLI script writes `out/runs/<timestamp>/{config.json, git_sha, inputs.sha256, outputs.sha256, stdout.log, duration.json}`.
- **Notebooks are not replication artifacts.** Anything that produces a number in the paper must live under `scripts/` or `src/`, not `notebooks/`.
- **Decision log.** `docs/decisions.md` — running ADR-style log of methodological choices (one entry per non-trivial judgment call, with rationale).
- **Preregistration.** The H1–H3 tests in §1.2 are preregistered — regression specs in §6.7 are frozen before Phase 6 results are unblinded. The agent should assert this in `docs/decisions.md` and refuse to modify §6.7 specs after Phase 6 runs.

---

## 8. Open Decisions

1. **Embedding model.** `bge-large-en-v1.5` (stable, well-validated) vs `nomic-embed-text-v1.5` (better on social text, permissive license) vs `Qwen3-Embedding-4B` (strongest benchmarks but heavier). Default: `nomic-embed-text-v1.5`. Reopen if mention-detection recall is weak.
2. **LLM adjudicator.** Gemma 4
3. **Emotion taxonomy.** GoEmotions' 27 categories vs collapsing to Plutchik-8. Default: keep 27 for scoring, report Plutchik-8 aggregates for interpretability. The "positive" / "negative" partition in the Saints equation needs an explicit mapping — propose a mapping in `docs/decisions.md` before Phase 6.
4. **Attacker-set scope.** Should near-miss / foiled attacks be included? Currently ambiguous in cases_audited.csv. Agent: surface the foiled cases with their metadata and ask.
5. **Post-cutoff attackers.** /pol/ dump ends 2021; several high-profile post-2021 attacks (Buffalo, Uvalde, Bratislava, Allen TX, Jacksonville) have no /pol/ coverage here. Recommend flagging them as out-of-sample and discussing in the limitations section rather than imputing.
6. **Thread-level vs post-level unit of analysis.** Post-level is primary; consider thread-level aggregation as a robustness check — flag decision before Phase 4.

---

## 9. Milestones

| # | Milestone | Deliverable | Gate |
|---|---|---|---|
| M1 | Corpus ingested | `pol/*.parquet`, manifest | Row-count + gap report approved |
| M2 | Mentions detected | `mentions.parquet`, eval report | Precision ≥ 0.90, recall ≥ 0.75 |
| M3 | Affect scored | `affect_scores.parquet`, α report | α ≥ 0.5 on sentiment & emotion |
| M4 | Temporal metrics | `temporal_metrics.parquet` | Decay fits inspected per attacker |
| M5 | Semantic metrics | `semantic_metrics.parquet` | Distributions inspected |
| M6 | Saints Score | naïve + Bayes scores | Face validity (Breivik/Tarrant/Roof high) |
| M7 | Regression | coefficient tables + figures | PPC + LOO reasonable |

The agent halts at each milestone, produces a one-page run summary in `out/runs/<timestamp>/SUMMARY.md`, and waits.

---

## 10. Non-goals

- Not building a live ingest from 4plebs' API; this project is the 2010–2021 dump only. (A separate pipeline handles the API.)
- Not producing actionable threat intelligence on named individuals beyond the already-public attacker set.
- Not fine-tuning foundation models in scope of this spec; use pretrained models. A follow-on phase may revisit.
- Not extending to Iron March or other platforms; those are separate chapters.