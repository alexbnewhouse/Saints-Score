# Saints Score

Quantifying attacker canonization in online extremist communities.

Saints Score is a computational pipeline that measures the degree to which perpetrators of mass-casualty violence are elevated, celebrated, or "sainted" by 4chan's /pol/ board. It ingests the full /pol/ corpus, detects attacker mentions via multi-stage weak supervision, scores affective tone and temporal dynamics, and produces a Bayesian latent-variable index (the Saints Score) for each attacker in a dataset of ~160 OECD mass-violence events (2001--2026).

This project supports Chapter 3 of a dissertation on computational political religion.

## Pipeline overview

The pipeline runs in eight sequential phases via a unified CLI (`saints-score`). Each phase reads upstream outputs and writes structured Parquet or CSV artifacts. Every run is logged with config snapshots, input/output hashes, and timing.

| Phase | Command | What it does |
|-------|---------|-------------||
| 1 | `saints-score ingest` | Stream-decompress the 4plebs /pol/ tar.gz, parse and normalize posts, write partitioned Parquet (year/month). Also validates the case dataset. |
| 2 | `saints-score mentions` | Multi-stage mention detection: seed alias inventory, lexical retrieval (exact + fuzzy + adversarial normalisation), semantic retrieval, LLM adjudication (Ollama), alias bootstrapping (up to 3 rounds). |
| 3 | `saints-score affect` | Classify sentiment (XLM-RoBERTa), emotion (GoEmotions), and toxicity on mention posts. GPU-accelerated with automatic batch sizing. |
| 4 | `saints-score temporal` | Compute intensity (mention proportion in immediate window), longevity (power-law decay fit), and daily mention time series per attacker. |
| 5 | `saints-score semantic` | Embed mention posts with `nomic-embed-text-v1.5` (fp16 on GPU), compute pairwise cosine similarity (semantic convergence) per attacker. |
| 6 | `saints-score score` | Assemble the composite Saints Score in two forms: a naive scaled composite and a one-factor Bayesian confirmatory model (PyMC) with 89% HDIs. |
| 7 | `saints-score regression` | Hierarchical Bayesian regression of Saints Score on attack characteristics (ideology, weapon, manifesto, livestream, casualties) with partial pooling on ideology and country. |
| 8 | `saints-score drift` | ConTEXT-inspired embedding drift analysis: track centroid migration, dispersion changes, and evasion rates over sliding post-attack windows. |

## The case dataset

The `out/` directory ships with a pre-built dataset of ~159 cases derived from 12 hand-coded markdown files (`part01`--`part12`). The conversion pipeline is:

1. **`convert.py`** -- Parses the `partXX_*.md` files into structured CSV/Parquet (`out/cases.csv`, `out/influences.csv`, plus auxiliary tables for platforms, handles, subculture tags, cross-references, etc.).
2. **`audit.py`** -- Validates every field against the schema (type checks, enum membership, range constraints). Flags issues in `out/audit_flags.csv`.
3. **`apply_audit.py`** -- Applies evidence-tier corrections, fills `how_disrupted` for partially-foiled cases, and produces the final `out/cases_audited.csv`.

The audited cases file is what Phase 1 ingests. See `docs/codebook.md` for the full variable dictionary.

### Key output files

| File | Description |
|------|-------------|
| `out/cases_audited.csv` | Final case dataset (159 cases, ~70 columns) |
| `out/influences.csv` | Directed attacker-to-attacker citation/influence edges |
| `out/cross_references.csv` | Cross-reference links between cases |
| `out/subculture_tags.csv` | Long-format subculture/tradition tags per case |
| `out/validation_corpus.csv` | Cases marked for hand-coded mention validation |
| `out/schema.json` | Machine-readable schema definition |

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (package manager)
- ~16 GB RAM for full /pol/ ingest; GPU recommended for Phases 2--5
- [Ollama](https://ollama.com/) running locally with `gemma3:27b` for LLM adjudication (Phase 2)

### Data dependencies (not in git)

| Path | What | How to obtain |
|------|------|---------------|
| `data/pol/pol.csv.tar.gz` | 4plebs /pol/ archive dump | [4plebs.org](https://4plebs.org/) data request |
| `data/raw/` | Any additional raw data | Manual placement |

## Setup

```bash
# Clone and enter
git clone <repo-url> && cd Saints-Score

# Create environment and install all dependencies (byte-reproducible via uv.lock)
make env

# Install pre-commit hooks
uv run pre-commit install

# Verify
make test-unit
make lint
make typecheck
```

## Running the pipeline

Each phase reads from `config.toml`. Override any setting via environment variables prefixed `SAINTS_` (e.g., `SAINTS_SEED=123`).

```bash
# Run individual phases
saints-score ingest --config config.toml
saints-score mentions --config config.toml
saints-score affect --config config.toml
saints-score temporal --config config.toml
saints-score semantic --config config.toml
saints-score score --config config.toml
saints-score regression --config config.toml
saints-score drift --config config.toml

# Run the entire pipeline end-to-end
saints-score run-all --config config.toml

# Make targets still work (they delegate to the CLI)
make ingest
make mentions
make run-all
```

Every command supports `--dry-run` (parse without writing) and `--limit N` (process only N rows, for smoke testing):

```bash
saints-score ingest --config config.toml --limit 10000 --dry-run
```

## Configuration

All tuning parameters, model IDs, paths, and temporal windows are centralized in `config.toml` under the `[saints_score]` table. The Pydantic Settings class (`src/saints_score/config.py`) merges values in this priority order:

1. Explicit kwargs
2. `SAINTS_*` environment variables
3. `config.toml` values
4. Hardcoded defaults

Key settings:

| Setting | Default | Description |
|---------|---------|-------------|
| `seed` | `20260414` | Global random seed |
| `embedding_model` | `nomic-ai/nomic-embed-text-v1.5` | Sentence embedding model |
| `adjudicator_model` | `gemma3:27b` | Ollama model for mention adjudication |
| `fuzzy_threshold` | `85` | RapidFuzz ratio threshold for fuzzy alias matching |
| `mention_confidence_threshold` | `0.5` | Minimum LLM confidence to accept a mention |
| `immediate_end` | `7` | Immediate post-attack window (days) |
| `longterm_end` | `730` | Long-term window end (days, ~2 years) |

## Project structure

```
Saints-Score/
├── config.toml                  # Pipeline configuration
├── Makefile                     # Common entry points
├── pyproject.toml               # Package metadata + tool config
│
├── src/saints_score/            # Core library
│   ├── cli.py                   # Unified Click CLI (saints-score command)
│   ├── __main__.py              # python -m saints_score entry point
│   ├── config.py                # Pydantic Settings (centralized config)
│   ├── logging.py               # Loguru setup
│   ├── affect/classify.py       # Sentiment, emotion, toxicity (GPU auto-batch)
│   ├── cases/loader.py          # Case dataset loading + Pandera validation
│   ├── ingest/pol.py            # /pol/ tar.gz → partitioned Parquet
│   ├── io/                      # Parquet I/O, tar streaming, run logging
│   ├── mentions/                # Alias building, lexical/semantic retrieval,
│   │                            #   adversarial normalisation, LLM adjudication
│   │   ├── adversarial.py       # Leetspeak, homoglyph, Zalgo, phonetic handling
│   │   └── ...                  #   bootstrapping
│   ├── models/regression.py     # Hierarchical Bayesian regression (PyMC)
│   ├── scoring/composite.py     # Naive + Bayesian Saints Score
│   ├── semantic/
│   │   ├── convergence.py       # Embedding similarity metrics
│   │   └── drift.py             # ConTEXT-inspired embedding drift analysis
│   ├── temporal/metrics.py      # Intensity, longevity, decay fitting
│   └── viz/plots.py             # Decay curves, forest plots, comparison plots
│
├── scripts/                     # Legacy CLI scripts (now delegated to cli.py)
│
├── convert.py                   # Markdown dataset → CSV/Parquet conversion
├── audit.py                     # Schema audit of raw cases
├── apply_audit.py               # Apply audit corrections → cases_audited.csv
│
├── out/                         # Pre-built case dataset + pipeline outputs
│
├── partXX_*.md                  # Hand-coded case dataset (12 parts)
│
├── tests/
│   ├── conftest.py              # Shared fixtures (Settings, sample cases/posts)
│   ├── unit/                    # 36 unit tests (config, ingest, IO, aliases,
│   │                            #   scoring, lexical, affect, temporal,
│   │                            #   adjudication, convergence)
│   └── integration/             # Integration tests (marked, need data)
│
└── docs/
    ├── codebook.md              # Variable definitions + temporal windows
    ├── decisions.md             # Architecture Decision Records (ADR-001 to 007)
    ├── mention_detection.md     # Multi-stage mention detection protocol
    └── scoring.md               # Naive + Bayesian scoring methodology
```

## Scoring methodology

The Saints Score is computed in two complementary forms:

**Naive Saints Score** -- A scaled composite:

```
Saints_a = z(log((E+ + eps) / (E- + eps))) * (I* + L* + S*)
```

where E+/E- are positive/negative sentiment proportions, I is intensity (immediate-window mention share), L is longevity (inverse power-law decay rate), and S is semantic convergence (median pairwise cosine similarity). All components are min-max scaled; the affect ratio is z-scored.

**Bayesian Saints Score** -- A one-factor confirmatory model in PyMC treating the Saints Score as a latent variable with five indicators (log affect ratio, intensity, longevity, semantic convergence, log mention volume). Returns posterior mean factor scores with 89% HDIs per attacker. See `docs/scoring.md` for full specification.

## Development

```bash
make lint          # Ruff linter + formatter check
make fmt           # Auto-format
make typecheck     # mypy strict
make test          # All tests
make test-unit     # Unit tests only
make clean         # Remove __pycache__, .mypy_cache, etc.
```

Ruff is configured for Python 3.12 with 99-char line length. mypy runs in strict mode with Pydantic plugin. Pre-commit hooks run ruff and basic file hygiene on every commit.

Optional visualization dependencies (plotnine, seaborn) are in the `viz` extra:

```bash
uv pip install -e ".[viz]"
```

## Design decisions

Key architectural choices are documented in `docs/decisions.md`:

- **ADR-001**: Embedding model -- `nomic-embed-text-v1.5` (permissive license, good on social media text)
- **ADR-002**: LLM adjudicator -- Gemma 3 27B via Ollama (local, no API costs)
- **ADR-003**: Emotion taxonomy -- GoEmotions 27 categories, reported as Plutchik-8 aggregates
- **ADR-004**: Unit of analysis -- Post-level primary, thread-level as robustness check
- **ADR-005**: Preregistration freeze -- H1--H3 tests and regression specs frozen before Phase 6 unblinding
- **ADR-006**: Post-2021 attackers -- Out-of-sample for /pol/ corpus (dump ends 2021-12)
- **ADR-007**: Foiled attacks -- TBD, surfaced with metadata pending decision
- **ADR-008**: Unified CLI -- Migrated from per-phase scripts to a single Click CLI group (`saints-score`)
- **ADR-009**: Adversarial language normalisation -- Leetspeak, homoglyphs, Zalgo stripping, and phonetic skeleton matching for evasion-resistant mention detection
- **ADR-010**: Embedding drift analysis -- ConTEXT-inspired sliding-window tracking of centroid migration, dispersion, and evasion rates
- **ADR-011**: GPU acceleration -- fp16 embeddings on CUDA, automatic batch sizing based on available VRAM

## Known limitations

- The /pol/ corpus dump ends December 2021. Post-2021 attackers appear in the case dataset but cannot receive Saints Scores from this corpus.
- Geographic coverage is weighted toward US, Europe, Japan, Russia, Korea, and Australia. Latin American OECD members, Baltic states, and southern European countries are thin.
- Most recent cases (2025--2026) have limited primary-source documentation.
- Russian juvenile cases have publication restrictions that limit evidence transparency.
- Evidence tiers are conservative: tier 1 requires court/coroner/official sources only.

## License

MIT
