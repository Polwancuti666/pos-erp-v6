.PHONY: help install dev test lint format build docker-up docker-down clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Setup ──────────────────────────────────────────

install: ## Install all dependencies (backend + frontend)
	python -m pip install -e ".[dev]"
	cd frontend && npm ci

dev: ## Start development servers (backend + frontend)
	@echo "Starting backend on :8000 and frontend on :5173..."
	@make -j2 dev-backend dev-frontend

dev-backend: ## Start backend dev server
	PYTHONPATH=src uvicorn pos_erp.fastapi_app:app --host 0.0.0.0 --port 8000 --reload

dev-frontend: ## Start frontend dev server
	cd frontend && npm run dev

# ── Quality ────────────────────────────────────────

test: ## Run all tests
	PYTHONPATH=src pytest tests/ -v --timeout=30

test-cov: ## Run tests with coverage
	PYTHONPATH=src pytest tests/ -v --timeout=30 --cov=src/pos_erp --cov-report=term-missing

lint: ## Lint Python code with ruff
	ruff check src/ tests/

lint-fix: ## Lint and auto-fix
	ruff check src/ tests/ --fix

format: ## Format Python code
	ruff format src/ tests/

typecheck: ## Type check with mypy
	mypy src/pos_erp/ --ignore-missing-imports --no-strict-optional

check-frontend: ## Type check frontend
	cd frontend && npx tsc --noEmit

check: lint typecheck check-frontend ## Run all checks (lint + typecheck + frontend)

# ── Build ──────────────────────────────────────────

build: ## Build frontend for production
	cd frontend && npm run build

build-docker: ## Build Docker image
	docker build -t pos-erp-v6:latest .

# ── Docker ─────────────────────────────────────────

up: ## Start services with Docker Compose
	docker-compose up -d

down: ## Stop services
	docker-compose down

logs: ## View Docker logs
	docker-compose logs -f

# ── Database ───────────────────────────────────────

db-reset: ## Reset database (WARNING: destroys data)
	dropdb pos_erp 2>/dev/null || true
	createdb pos_erp
	@echo "Database reset. Restart backend to apply schema."

db-shell: ## Open psql shell
	psql -U erp -d pos_erp

# ── Deployment ─────────────────────────────────────

deploy: ## Deploy to production (via SSH)
	bash scripts/deploy.sh

# ── Cleanup ────────────────────────────────────────

clean: ## Remove build artifacts
	rm -rf frontend/dist/ frontend/node_modules/ .venv/ __pycache__/ .pytest_cache/
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
