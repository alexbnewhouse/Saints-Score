# Saints Score -- Technical Specification

## 1. Research question

To what degree does 4chan's /pol/ board canonize perpetrators of mass-casualty violence, and which attack characteristics predict higher canonization?

### 1.1 Concept

The "Saints Score" is a continuous latent variable measuring the degree to which an online community elevates a mass-violence perpetrator into its symbolic pantheon. It is operationalized through five observable indicators extracted from the /pol/ corpus:

1. **Affect ratio** -- log(positive sentiment / negative sentiment) across all mention posts
2. **Intensity** -- proportion of board-wide posts that mention the attacker in the immediate post-attack window (t to t+7 days)
3. **Longevity** -- inverse decay rate (1/alpha) from a power-law fit to daily mention counts
4. **Semantic convergence** -- median pairwise cosine similarity of mention-post embeddings (higher = more formulaic/ritualized language)
5. **Mention volume** -- log-transformed total mention count

### 1.2 Hypotheses (preregistered, frozen before Phase 6)

- **H1**: Attackers who produced a manifesto receive higher Saints Scores than those who did not.
- **H2**: Attackers who livestreamed receive higher Saints Scores than those who did not.
- **H3**: Saints Score is positively associated with the number of subsequent attackers who cite the perpetrator (outgoing citation count in the influence network).

## 2. Data sources

### 2.1 Case dataset

~160 mass-violence events in OECD countries, 2001--2026. Hand-coded from primary sources (court records, coroner reports, official investigations) across 12 markdown files (`part01`--`part12`). Variables include attack metadata, perpetrator demographics, weapon details, manifesto/livestream indicators, ideology classifications, subculture tags, and a directed citation network.

The full variable dictionary is in `docs/codebook.md`.

### 2.2 /pol/ corpus

4plebs archival dump of 4chan /pol/. CSV compressed as tar.gz. Columns follow the 4plebs schema (27 fields per post). The pipeline normalizes to a canonical schema:

| Column | Type | Description |
|--------|------|-------------|
| `post_id` | int | Globally unique post number |
| `thread_id` | int | Thread OP post number |
| `board` | str | Always "pol" |
| `timestamp_utc` | datetime | UTC timestamp |
| `poster_id` | str | Ephemeral per-thread poster ID |
| `title` | str | Post title (usually null) |
| `body` | str | HTML-stripped post body |
| `body_clean` | str | NFKC-normalized, lowercased, whitespace-collapsed |
| `reply_to` | list[int] | Extracted >>NNN reply references |
| `has_image` | bool | Whether post has an attached image |
| `country_code` | str | Poster country flag |

Partitioned on disk as Hive-style `year=YYYY/month=MM/*.parquet`.

## 3. Pipeline phases

### 3.1 Phase 1: Ingest (`01_ingest_pol.py`)

- Stream-decompress tar.gz in configurable chunks (default 1M rows)
- Parse 4plebs CSV, normalize columns, strip HTML, NFKC-normalize body text
- Write partitioned Parquet with SHA-256 manifest
- Separately: load, validate (Pandera), and persist case dataset

### 3.2 Phase 2: Mention detection (`02_detect_mentions.py`)

Multi-stage weak supervision to find attacker references in adversarially-evolved text:

1. **Seed alias inventory** -- canonical name, news aliases, Wikipedia redirects, KnowYourMeme, online handles
2. **Lexical retrieval** -- exact substring (case-insensitive) + RapidFuzz ratio >= 85 on tokens >= 4 chars
3. **Semantic retrieval** -- embed natural-language probes, retrieve top-k nearest neighbors
4. **LLM adjudication** -- local Ollama model (Gemma 3 27B) classifies each candidate with structured output: `{is_reference, confidence, inferred_alias, is_oblique}`
5. **Alias bootstrapping** -- extract high-TF-IDF tokens from positive adjudications, promote to alias inventory, iterate stages 2--4 up to 3 rounds

Validation target: precision >= 0.90, recall >= 0.75 on hand-coded stratified sample (200 posts per attacker).

### 3.3 Phase 3: Affect scoring (`03_score_affect.py`)

Three transformer classifiers applied to all mention posts:

- **Sentiment**: `cardiffnlp/twitter-xlm-roberta-base-sentiment` (positive/neutral/negative)
- **Emotion**: `SamLowe/roberta-base-go_emotions` (27 GoEmotions categories, aggregated to Plutchik-8)
- **Toxicity**: `unitary/unbiased-toxic-roberta`

### 3.4 Phase 4: Temporal metrics (`04_compute_temporal.py`)

Per attacker:
- Daily mention counts across the full corpus time range
- **Intensity** (I_a): mention proportion in the immediate window [t, t+7d] relative to total board activity
- **Longevity** (L_a): 1/alpha from power-law decay fit (C * t^{-alpha}) on daily counts post-attack
- Decay curve visualization per attacker

Temporal windows are configurable:
- Baseline: t-365d to t-1d
- Immediate: t to t+7d
- Near-term: t+8d to t+90d
- Long-term: t+91d to t+730d

### 3.5 Phase 5: Semantic convergence (`05_compute_semantic.py`)

- Embed all mention posts per attacker with `nomic-embed-text-v1.5`
- Compute pairwise cosine similarity matrix
- Report median similarity (S_a) as the convergence metric
- Higher convergence = more formulaic/ritualized community discourse about the attacker

### 3.6 Phase 6: Saints Score assembly (`06_assemble_saints_score.py`)

**Naive score**:
```
Saints_a = z(log((E+ + eps) / (E- + eps))) * (I* + L* + S*)
```

Where I*, L*, S* are min-max scaled; affect ratio is z-scored across attackers.

**Bayesian score** (one-factor confirmatory model in PyMC):
```
y_{aj} = lambda_j * eta_a + epsilon_{aj}
eta_a ~ Normal(0, 1)
lambda_j ~ Normal(0.5, 1)
sigma_j ~ HalfNormal(1)
epsilon_{aj} ~ Normal(0, sigma_j)
```

Five indicators standardized before fitting. Output: posterior mean factor scores with 89% HDIs. Diagnostics: PPC, LOO.

### 3.7 Phase 7: Regression (`07_fit_attack_regression.py`)

Hierarchical Bayesian regression:

- **DV**: Posterior-mean Bayesian Saints Score
- **IVs**: log(casualties), manifesto (binary), livestream (binary), perpetrator age (standardized)
- **Partial pooling**: ideology tradition (n groups), country (n groups)

```
mu = intercept + X*beta + alpha_ideology[i] + alpha_country[j]
y ~ Normal(mu, sigma)
```

Output: coefficient table with 89% HDIs, forest plot, InferenceData (.nc).

## 4. Reproducibility

- Global random seed in `config.toml` (default: 20260414)
- Every pipeline run logs: config snapshot, git SHA, input/output SHA-256 hashes, wall-clock duration, phase-specific metrics
- Run logs are written to `out/runs/<timestamp>_<phase>/`
- `uv.lock` ensures byte-reproducible environments
- Preregistration freeze (ADR-005): regression specifications cannot be modified after Phase 6 results are unblinded

## 5. Validation strategy

- **Mention detection**: hand-coded stratified sample, 200 posts per attacker. Target: precision >= 0.90, recall >= 0.75.
- **Affect scoring**: domain-validity review after Phase 3 (do sentiment distributions match qualitative expectations for known high/low cases?)
- **Temporal metrics**: visual inspection of decay curves; Paddock (Las Vegas) should show no sustained elevation
- **Saints Score**: face validity check -- Tarrant (Christchurch) should rank near top; Paddock should rank near bottom
- **Regression**: PPC (posterior predictive checks) and LOO (leave-one-out cross-validation) diagnostics

## 6. Known constraints

- /pol/ corpus ends December 2021. Post-2021 attackers are in the case dataset but cannot receive corpus-derived Saints Scores.
- Board-level activity denominators may conflate general /pol/ volume spikes (elections, major news) with attacker-specific effects. Baseline windows partially mitigate this.
- LLM adjudication introduces model-specific bias. Cached outputs are keyed on model+version for reproducibility.
- Foiled attacks (status=F, PF) have heterogeneous media profiles; inclusion decision pending (ADR-007).
