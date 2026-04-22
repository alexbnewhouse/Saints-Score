# Mention Detection Protocol

## Overview

Attacker mention detection is the hardest phase of the Saints Score pipeline.
/pol/ users adversarially evolve spellings, use oblique references, memes, and
coded language. A purely lexical approach will miss a large proportion of
references. This document describes the multi-stage weak supervision approach.

## Stages

### Stage 1: Seed Alias Inventory

For each attacker, we assemble a seed list of aliases from:
- Canonical name from case metadata
- News-reported aliases
- Wikipedia redirects
- KnowYourMeme entries
- Online handles from case metadata

Stored in `data/processed/aliases_seed.parquet`.

### Stage 2: Lexical Candidate Retrieval

For each seed alias:
1. **Exact substring** (case-insensitive) on `body_clean`
2. **Fuzzy matching** via `rapidfuzz` ratio ≥ 85 on tokens ≥ 4 chars
3. Phonetic matching as recall boost

This stage deliberately over-retrieves; precision is handled downstream.

### Stage 2.5: Adversarial Normalisation

After exact/fuzzy matching and before semantic retrieval, posts are passed
through an adversarial normalisation pipeline (`mentions/adversarial.py`):

1. **NFKC normalisation** — Unicode compatibility decomposition
2. **Homoglyph replacement** — Cyrillic/Greek look-alikes mapped to Latin equivalents (e.g., `В` → `B`, `ε` → `e`)
3. **Zalgo stripping** — Remove runs of 2+ combining diacritical marks
4. **Leetspeak decoding** — Common substitutions reversed (e.g., `4` → `a`, `1` → `i`, `$` → `s`)
5. **Repeated character collapse** — Reduce runs of 3+ identical characters to 2 (e.g., `Taaaarrant` → `Taarrant`)
6. **Lowercase normalisation**

After normalisation, two matching passes are applied:
- **Normalised exact match** (score 0.9, type `adversarial_norm`) — Normalised post text is checked against adversarial variants of seed aliases
- **Consonant skeleton match** (score 0.8, type `phonetic_skeleton`) — Vowels are stripped and consecutive duplicate consonants are collapsed (e.g., `tarrant` → `trnt`), then matched against skeleton variants of aliases

This stage catches evasive spellings like `T4rr4nt`, `Βrеntоn` (mixed scripts),
and Z̷̧a̵l̸g̶o̵-̸o̷b̵f̶u̵s̶c̴a̴t̴e̵d̸ text that would defeat exact and fuzzy matching.

### Stage 3: Semantic Candidate Retrieval

For each attacker, construct natural-language probes and embed with the
configured sentence-transformer model. Retrieve top-k nearest neighbours.

### Stage 4: Cross-Encoder Adjudication

Candidates are classified by a GPU-native `sentence-transformers` CrossEncoder
(`cross-encoder/ms-marco-MiniLM-L-6-v2`) using a **tiered confidence strategy**:

**Tier 1 — exact_substring** (auto-accept)
`exact_substring` matches are accepted unconditionally with `confidence = 1.0`.
These are verified alias hits; cross-encoder scoring would only add noise.

**Tier 2 — cross-encoder** (fuzzy, adversarial_norm, phonetic_skeleton, semantic)
Each remaining candidate pair `("Does this post reference {name}?", post_text[:512])`
is scored by the cross-encoder.  The raw logit is converted to a probability via
sigmoid.  Candidates with `confidence ≥ mention_confidence_threshold` (default 0.5)
are accepted.

**Output fields**
- `is_reference: bool` — accepted by tier 1 or cross-encoder threshold
- `confidence: float` — 1.0 for exact hits; sigmoid(logit) otherwise
- `inferred_alias: str | null` — lexical alias if present, else null
- `is_oblique: bool` — True for `semantic` or `phonetic_skeleton` match types
  (heuristic: these represent indirect/encoded references)

Results are cached to `data/processed/adjudication_cache.parquet` keyed on
`(post_id, attacker_id, model_name)`.  Re-runs skip already-scored pairs.

**Performance**: ~50 000 pairs/second on an RTX 5080.  The ~186 K non-exact
candidates are scored in under 4 seconds.

### Stage 5: Alias Bootstrapping

From positive adjudications, extract high-TF-IDF tokens and n-grams that
co-occur disproportionately with the attacker. Human review promotes
survivors to the alias inventory. Iterate stages 2–5 up to 3 rounds.

### Stage 6: Oblique Reference Handling

Posts with `is_oblique=True` are maintained in a separate table with
provenance. The `is_oblique` flag is set heuristically for `semantic` and
`phonetic_skeleton` match types, which surface indirect or encoded references.
Examples:
- "subscribe to PewDiePie" → Tarrant (semantic match)
- "Knights Templar" → Breivik (semantic match)
- "t4rr4nt" → Tarrant (phonetic_skeleton match)

## Validation

Hand-coded stratified sample of 200 posts per attacker.
Target: **precision ≥ 0.90, recall ≥ 0.75** at final threshold.
