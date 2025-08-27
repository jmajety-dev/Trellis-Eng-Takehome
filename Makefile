.PHONY: help build up down logs migrate test test-unit test-integration clean start-order

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build Docker images
	docker-compose build

up: ## Start all services (Temporal, PostgreSQL, Worker)
	docker-compose up -d
	@echo "Waiting for services to start..."
	@sleep 10
	@echo "Services started. Temporal Web UI: http://localhost:8080"

down: ## Stop all services
	docker-compose down

logs: ## Show logs from all services
	docker-compose logs -f

logs-worker: ## Show worker logs
	docker-compose logs -f worker

migrate: ## Run database migrations
	python scripts/migrate.py

test: ## Run all tests
	python -m pytest

test-unit: ## Run unit tests only
	python -m pytest tests/unit/

test-integration: ## Run integration tests only
	python -m pytest tests/integration/

clean: ## Clean up Docker volumes and containers
	docker-compose down -v
	docker system prune -f

install: ## Install Python dependencies
	pip install -r requirements.txt

dev-setup: install migrate ## Setup development environment
	@echo "Development environment ready!"

api: ## Start the FastAPI server
	python -m uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload

# Example commands for testing
start-order: ## Start a test order (example)
	python scripts/cli.py start order-123 payment-456 '[{"sku":"ABC","qty":2}]' --address '{"street":"123 Main St","city":"Seattle"}'

approve-order: ## Approve a test order (example)
	python scripts/cli.py signal order-123 approve --data "CLI approval"

cancel-order: ## Cancel a test order (example)
	python scripts/cli.py signal order-123 cancel --data "CLI cancellation"

order-status: ## Get order status (example)
	python scripts/cli.py status order-123

# Complete workflow example
demo: up ## Run a complete demo workflow
	@echo "Starting demo workflow..."
	@sleep 5
	@echo "1. Starting order..."
	@python scripts/cli.py start demo-order payment-demo '[{"sku":"DEMO","qty":1}]' --address '{"street":"123 Demo St","city":"DemoCity"}' || true
	@sleep 2
	@echo "2. Checking status..."
	@python scripts/cli.py status demo-order || true
	@sleep 3
	@echo "3. Approving order..."
	@python scripts/cli.py signal demo-order approve --data "Demo approval" || true
	@sleep 5
	@echo "4. Final status..."
	@python scripts/cli.py status demo-order || true
	@echo "Demo completed!"
