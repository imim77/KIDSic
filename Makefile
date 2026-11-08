# .env is not loaded automatically, so default to the docker compose database.
export DATABASE_URL ?= postgresql://kidsic:kidsic_local@localhost:55432/kidsic

SETUP_STAMP := .setup-done
ALEMBIC := uv run alembic -c src/KIDSic/db/alembic/alembic.ini

# Help generator
help: ## Display this help.
	@echo "Please use 'make <target>' where <target> is one of the following:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

start: ## Set up on first run, then start API, MCP server and frontend
	@test -f $(SETUP_STAMP) || $(MAKE) setup
	@echo "API: http://127.0.0.1:8000  MCP: http://127.0.0.1:8001/mcp  Frontend: http://127.0.0.1:5173"
	$(MAKE) -j3 run-api run-mcp run-frontend

setup: sync install-frontend up migrate register-sources sync-kindergartens build-mcp ## First-time setup: dependencies, database, data import, MCP build
	@touch $(SETUP_STAMP)

stop: down ## Stop the database container

install-uv: ## Install uv package manager
	@if ! command -v uv >/dev/null 2>&1; then \
		echo "Installing uv package manager..."; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
	else \
		echo "uv is already installed"; \
	fi

sync: install-uv ## Sync the Python project
	uv sync

install-frontend: ## Install frontend dependencies
	npm --prefix frontend install

up: ## Start all containers
	docker compose up -d --wait

down: ## Stop all containers
	docker compose down

down-volumes: ## Stop all containers and remove volumes
	docker compose down -v

create-migrations: install-uv ## Create new database migration (usage: make create-migrations MESSAGE="add column")
	$(ALEMBIC) revision --autogenerate -m "${MESSAGE}"

migrate: install-uv up ## Apply database migrations
	$(ALEMBIC) upgrade head

register-sources: install-uv ## Register CKAN sources (usage: make register-sources args="--dry-run")
	uv run kidsic-register-sources ${args}

sync-kindergartens: install-uv ## Import kindergartens (usage: make sync-kindergartens args="--source national")
	uv run kidsic-sync-kindergartens ${args}

sync-historical: install-uv ## Import historical programs (usage: make sync-historical args="--dry-run")
	uv run kidsic-sync-historical ${args}

sync-enrolment: install-uv ## Import enrolment data (usage: make sync-enrolment args="--dry-run")
	uv run kidsic-sync-enrolment ${args}

run-api: ## Run the HTTP locations API on port 8000
	PYTHONDONTWRITEBYTECODE=1 uv run uvicorn KIDSic.api.locations:create_app --factory --reload --host 127.0.0.1 --port 8000

run-mcp: build-mcp ## Run the MCP server on port 8001
	PYTHONDONTWRITEBYTECODE=1 uv run uvicorn KIDSic.api.mcp_server:create_app --factory --host 127.0.0.1 --port 8001

run-frontend: ## Run the frontend dev server
	npm --prefix frontend run dev

build-frontend: ## Build the frontend
	npm --prefix frontend run build

build-mcp: ## Build the standalone MCP view
	npm --prefix frontend run build:mcp

lint-frontend: ## Lint the frontend
	npm --prefix frontend run lint

test: install-uv ## Run Python tests (integration tests need KIDSIC_TEST_DATABASE_URL)
	uv run python -m unittest discover -s tests -v ${args}

test-frontend: ## Run frontend tests
	npm --prefix frontend run test

clean-pyc: ## Remove Python cache files
	find . -type d -name "__pycache__" -not -path "./.venv/*" -not -path "./frontend/node_modules/*" -exec rm -r {} +
	find . -type f \( -name "*.pyc" -o -name "*.pyo" -o -name "*.pyd" \) -not -path "./.venv/*" -delete

command: install-uv up ## Run a Python module (usage: make command COMMAND_WITH_ARGS="scripts/import_sibenik.py --apply")
	uv run python ${COMMAND_WITH_ARGS}

.PHONY: $(shell grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | cut -d ':' -f 1)
