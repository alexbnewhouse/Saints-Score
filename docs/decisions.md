# Methodological Decision Log

Architecture Decision Records (ADR) for the Saints Score pipeline.

---

## ADR-001: Embedding Model Selection

**Date:** 2026-04-19
**Status:** Decided
**Decision:** Use `nomic-ai/nomic-embed-text-v1.5` as the default embedding model.
**Rationale:** Good performance on social media text, permissive license, reasonable
size. `bge-large-en-v1.5` is the fallback if recall is weak. `Qwen3-Embedding-4B`
is too heavy for the main pipeline but could be used for validation.

---

## ADR-002: LLM Adjudicator

**Date:** 2026-04-19
**Status:** Decided
**Decision:** Use Gemma 4 (via Ollama) for mention adjudication.
**Rationale:** Per spec §8.

---

## ADR-003: Emotion Taxonomy

**Date:** 2026-04-19
**Status:** Decided
**Decision:** Keep GoEmotions' 27 categories for scoring; report Plutchik-8
aggregates for interpretability. The positive/negative partition for the Saints
equation mapping is TBD — to be defined before Phase 6.

---

## ADR-004: Post-level Unit of Analysis

**Date:** 2026-04-19
**Status:** Decided
**Decision:** Post-level is primary. Thread-level aggregation will be computed
as a robustness check before Phase 4.

---

## ADR-005: Preregistration Freeze

**Date:** 2026-04-19
**Status:** Active
**Decision:** H1–H3 tests (§1.2) and regression specs (§6.7) are frozen before
Phase 6 results are unblinded. This code will refuse to modify regression specs
after Phase 6 runs. Any exploratory analyses must be clearly labelled as such
in the output.

---

## ADR-006: Post-2021 Attackers

**Date:** 2026-04-19
**Status:** Decided
**Decision:** Attacks after 2021 are out-of-sample for the /pol/ corpus (dump
ends 2021-12). Flag in limitations section rather than imputing.

---

## ADR-007: Foiled Attacks

**Date:** 2026-04-19
**Status:** Open — awaiting Alex's decision
**Decision:** TBD — surface foiled cases with metadata and ask Alex whether to
include in the Saints Score computation.

---

## ADR-008: Unified CLI

**Date:** 2026-04-20
**Status:** Decided
**Decision:** Replace per-phase standalone scripts with a single Click CLI group
(`saints-score`). Entry point registered via `[project.scripts]` in pyproject.toml.
**Rationale:** A unified CLI surface simplifies invocation (`saints-score ingest`
instead of `uv run python scripts/01_ingest_pol.py`), supports `--help` discovery,
and allows a single `run-all` command for full pipeline execution. Makefile targets
are retained as convenience wrappers. The `scripts/` directory is kept for backward
compatibility but all logic lives in `src/saints_score/cli.py`.

---

## ADR-009: Adversarial Language Normalisation

**Date:** 2026-04-20
**Status:** Decided
**Decision:** Add a pre-fuzzy adversarial normalisation stage to mention detection
(`mentions/adversarial.py`) that handles leetspeak, homoglyphs (Cyrillic/Greek
look-alikes), Zalgo text, repeated characters, and phonetic skeleton matching.
**Rationale:** /pol/ users routinely evade keyword detection via character
substitution (e.g., `T4rr4nt`, `Βrenton`). The literature on adversarial hate
speech (Ali, Blackburn & Stringhini 2025; Bermudez-Villalva 2025) confirms that
normalisation layers significantly improve recall without harming precision. The
consonant-skeleton matcher provides a fallback for creative misspellings that
survive character-level normalisation.

---

## ADR-010: Embedding Drift Analysis

**Date:** 2026-04-20
**Status:** Decided
**Decision:** Add a post-pipeline drift analysis phase (`semantic/drift.py`) that
tracks how the embedding-space location and dispersion of attacker mentions evolve
over sliding time windows after each attack.
**Rationale:** Inspired by Rodriguez, Spirling & Stewart (2023) *conText* (APSR)
and Kutuzov et al. (2018) diachronic word embeddings. Tracking centroid migration
and dispersion over time reveals whether community discourse converges on a stable
"saint" narrative or fragments. Evasion-rate tracking (via adversarial normalisation
match rates) provides an independent signal of community self-awareness of moderation.

---

## ADR-011: GPU Acceleration

**Date:** 2026-04-20
**Status:** Decided
**Decision:** Enable fp16 (half-precision) inference for embedding and
classification models when a CUDA GPU is available; auto-scale batch sizes based
on reported VRAM.
**Rationale:** The /pol/ corpus is large (~28 GB compressed). fp16 halves memory
footprint with negligible quality loss for our similarity and classification tasks.
Automatic batch scaling (VRAM-based) avoids OOM on smaller GPUs and under-utilisation
on larger ones.
