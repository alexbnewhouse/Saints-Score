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
