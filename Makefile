# Saints Score Pipeline
# ====================
# Common entry points for the Saints Score pipeline.
# Usage: make <target>

.PHONY: help env lint typecheck test test-unit test-integration ingest mentions affect temporal semantic score regression clean

PYTHON := python
UV := uv

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Environment ──

env: ## Create/sync the virtual environment (byte-reproducible)
	$(UV) sync --locked

lock: ## Regenerate uv.lock
	$(UV) lock

# ── Quality ──

lint: ## Run ruff linter + formatter check
	$(UV) run ruff check src/ scripts/ tests/
	$(UV) run ruff format --check src/ scripts/ tests/

fmt: ## Auto-format with ruff
	$(UV) run ruff check --fix src/ scripts/ tests/
	$(UV) run ruff format src/ scripts/ tests/

typecheck: ## Run mypy strict on core modules
	$(UV) run mypy src/saints_score/

# ── Testing ──

test: ## Run all tests
	$(UV) run pytest tests/ -v

test-unit: ## Run unit tests only
	$(UV) run pytest tests/unit/ -v

test-integration: ## Run integration tests only
	$(UV) run pytest tests/integration/ -v -m integration

# ── Pipeline phases ──

ingest: ## Phase 1: Ingest and normalize /pol/
	$(UV) run saints-score ingest --config config.toml

cases: ## Validate and produce cases.parquet
	$(UV) run saints-score ingest --config config.toml --cases-only

mentions: ## Phase 2: Detect attacker mentions
	$(UV) run saints-score mentions --config config.toml

affect: ## Phase 3: Score affect (sentiment + emotion)
	$(UV) run saints-score affect --config config.toml

temporal: ## Phase 4: Compute temporal metrics
	$(UV) run saints-score temporal --config config.toml

semantic: ## Phase 5: Compute semantic convergence
	$(UV) run saints-score semantic --config config.toml

score: ## Phase 6: Assemble composite Saints Score
	$(UV) run saints-score score --config config.toml

regression: ## Phase 7: Fit attack-characteristic regression
	$(UV) run saints-score regression --config config.toml

drift: ## Phase 8: Embedding-space drift analysis
	$(UV) run saints-score drift --config config.toml

run-all: ## Run full pipeline end-to-end
	$(UV) run saints-score run-all --config config.toml

# ── Housekeeping ──

clean: ## Remove intermediate build artifacts (NOT data)
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ *.egg-info
