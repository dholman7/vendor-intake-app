.DEFAULT_GOAL := help
BACKEND := backend

.PHONY: help install seed api test lint typecheck check

help: ## List targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

install: ## Install backend dependencies
	cd $(BACKEND) && uv sync

seed: ## Load demo tenants, users, and vendors (password: demo-password)
	cd $(BACKEND) && uv run python -m vendor_intake.seed

api: ## Run the API on :8000 with reload
	cd $(BACKEND) && uv run uvicorn vendor_intake.main:create_app --factory --reload --port 8000

test: ## Run backend tests with coverage
	cd $(BACKEND) && uv run pytest --cov=vendor_intake --cov-report=term-missing

lint: ## Lint and format-check the backend
	cd $(BACKEND) && uv run ruff check . && uv run ruff format --check .

typecheck: ## Type-check the backend (mypy strict)
	cd $(BACKEND) && uv run mypy src tests

check: lint typecheck test ## Everything CI runs for the backend
