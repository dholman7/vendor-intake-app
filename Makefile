.DEFAULT_GOAL := help
BACKEND := backend

.PHONY: help install seed api web dev test lint typecheck check openapi types e2e up down

help: ## List targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

install: ## Install backend dependencies
	cd $(BACKEND) && uv sync

seed: ## Load demo tenants, users, and vendors (password: demo-password)
	cd $(BACKEND) && uv run python -m vendor_intake.seed

api: ## Run the API on :8000 with reload
	cd $(BACKEND) && uv run uvicorn vendor_intake.main:create_app --factory --reload --port 8000

web: ## Run the Next.js dev server on :3000
	npm --prefix frontend run dev

dev: seed ## Seed, then run API and web together (Ctrl-C stops both)
	@trap 'kill 0' INT TERM; $(MAKE) api & $(MAKE) web & wait

test: ## Run backend tests with coverage
	cd $(BACKEND) && uv run pytest --cov=vendor_intake --cov-report=term-missing

lint: ## Lint and format-check the backend
	cd $(BACKEND) && uv run ruff check . && uv run ruff format --check .

typecheck: ## Type-check the backend (mypy strict)
	cd $(BACKEND) && uv run mypy src tests

check: lint typecheck test ## Everything CI runs for the backend

openapi: ## Regenerate openapi.json from the API code
	cd $(BACKEND) && uv run python -m vendor_intake.export_openapi ../openapi.json

types: openapi ## Regenerate openapi.json and the frontend's TypeScript types
	npm --prefix frontend run gen:types

e2e: ## Run the Playwright suite (starts both servers on a fresh database)
	cd e2e && npx playwright test

up: ## Build and run the whole app in Docker at http://localhost:3000
	NODE_VERSION=$$(cat .nvmrc) docker compose up --build

down: ## Stop the Docker stack
	docker compose down
