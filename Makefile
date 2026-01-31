.PHONY: help setup herald manor-api manor-ui almanac test lint clean docker-up docker-down

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Initial project setup
	@bash setup.sh

# --- Services ---

herald: ## Run herald (Telegram bot)
	cd packages/herald && python -m herald.main

manor-api: ## Run Manor API backend (port 8700)
	cd manor/api && uvicorn main:app --reload --port 8700

manor-ui: ## Run Manor frontend (port 3000)
	cd manor && npm run dev

almanac: ## Run almanac scheduler
	cd packages/almanac && python -m almanac.main

all: ## Run herald + manor-api + manor-ui (use with make -j3)
	@echo "Run with: make -j3 herald manor-api manor-ui"

# --- Development ---

test: ## Run all tests
	PYTHONPATH=packages/common:packages/herald:packages/steward:packages/almanac pytest tests/ -v

test-common: ## Run common package tests
	PYTHONPATH=packages/common pytest tests/test_watchtower.py tests/test_outbox.py tests/test_models.py tests/test_skills.py tests/test_db.py -v

lint: ## Lint Python code
	ruff check packages/ tests/

lint-fix: ## Lint and auto-fix Python code
	ruff check --fix packages/ tests/

format: ## Format Python code
	ruff format packages/ tests/

typecheck: ## Type check Python code
	mypy packages/common packages/herald packages/steward packages/almanac --ignore-missing-imports

# --- Manor ---

manor-install: ## Install Manor npm dependencies
	cd manor && npm install

manor-build: ## Build Manor for production
	cd manor && npm run build

manor-lint: ## Lint Manor TypeScript
	cd manor && npm run lint

# --- Docker ---

docker-up: ## Start all services via Docker
	docker compose up -d --build

docker-down: ## Stop all Docker services
	docker compose down

docker-logs: ## Tail Docker logs
	docker compose logs -f

# --- Data ---

clean-data: ## Remove all homestead data (DESTRUCTIVE)
	@echo "This will delete ~/.homestead - are you sure? [y/N]"
	@read ans && [ "$$ans" = "y" ] && rm -rf ~/.homestead || echo "Cancelled"

clean: ## Remove build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf manor/.next manor/node_modules/.cache

# --- Utilities ---

db-shell: ## Open SQLite shell for watchtower
	sqlite3 ~/.homestead/watchtower.db

logs: ## Show recent watchtower logs
	sqlite3 ~/.homestead/watchtower.db "SELECT datetime(timestamp, 'unixepoch', 'localtime'), level, source, message FROM logs ORDER BY timestamp DESC LIMIT 20"

sessions: ## List all herald sessions
	sqlite3 packages/herald/data/sessions.db "SELECT chat_id, name, model, is_active, message_count, datetime(last_active_at, 'unixepoch', 'localtime') FROM sessions ORDER BY last_active_at DESC"

tasks: ## List all steward tasks
	sqlite3 ~/.homestead/steward/tasks.db "SELECT substr(id,1,8), title, status, priority FROM tasks ORDER BY created_at DESC LIMIT 20" 2>/dev/null || echo "No tasks yet"

outbox: ## Show recent outbox messages
	sqlite3 ~/.homestead/outbox.db "SELECT id, agent_name, substr(message,1,60), status, datetime(created_at, 'unixepoch', 'localtime') FROM outbox ORDER BY created_at DESC LIMIT 10" 2>/dev/null || echo "No outbox messages"
