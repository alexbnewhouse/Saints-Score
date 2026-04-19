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

### Stage 3: Semantic Candidate Retrieval

For each attacker, construct natural-language probes and embed with the
configured sentence-transformer model. Retrieve top-k nearest neighbours.

### Stage 4: LLM Adjudication

Each candidate is classified by a local LLM (via Ollama) using a structured
few-shot prompt. The LLM returns:
- `is_reference: bool`
- `confidence: float`
- `inferred_alias: str | null`
- `is_oblique: bool`

All LLM outputs are cached (keyed on hash of prompt + model + version).

### Stage 5: Alias Bootstrapping

From positive adjudications, extract high-TF-IDF tokens and n-grams that
co-occur disproportionately with the attacker. Human review promotes
survivors to the alias inventory. Iterate stages 2–5 up to 3 rounds.

### Stage 6: Oblique Reference Handling

Posts classified as `is_oblique=True` are maintained in a separate table
with provenance. Examples:
- "subscribe to PewDiePie" → Tarrant
- "Knights Templar" → Breivik
- "disco tier" → Crusius

## Validation

Hand-coded stratified sample of 200 posts per attacker.
Target: **precision ≥ 0.90, recall ≥ 0.75** at final threshold.
