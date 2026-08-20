.PHONY: help dev build test lint clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# --- Docker ---

dev: ## Start all services in development mode
	docker compose up --build

dev-down: ## Stop all services
	docker compose down

build: ## Build all Docker images
	docker compose build

# --- Frontend ---

frontend-dev: ## Start frontend dev server
	cd frontend && npm run dev

frontend-build: ## Build frontend for production
	cd frontend && npm run build

frontend-lint: ## Lint frontend code
	cd frontend && npm run lint

# --- Backend ---

backend-dev: ## Start backend dev server
	cd backend && uvicorn src.main:app --reload

backend-test: ## Run backend tests
	cd backend && pytest -v

backend-lint: ## Lint backend code
	cd backend && ruff check src/ tests/

# --- ML ---

ml-test: ## Run ML tests
	cd ml && pytest -v

ml-lint: ## Lint ML code
	cd ml && ruff check src/ tests/

# --- Simulation ---

sim-test: ## Run simulation tests
	cd simulation && pytest -v

sim-lint: ## Lint simulation code
	cd simulation && ruff check src/ tests/

# --- All ---

test: backend-test ml-test sim-test ## Run all tests

lint: frontend-lint backend-lint ml-lint sim-lint ## Lint all code

clean: ## Clean build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name node_modules -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .next -exec rm -rf {} + 2>/dev/null || true
