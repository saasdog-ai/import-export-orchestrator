.PHONY: help install install-dev test lint format mypy clean run docker-build docker-up docker-down docker-logs migrate migrate-upgrade migrate-downgrade check pre-push

help:
	@echo "Available commands:"
	@echo "  make install       - Install production dependencies"
	@echo "  make install-dev   - Install development dependencies"
	@echo "  make test          - Run tests with coverage"
	@echo "  make lint          - Run ruff linter"
	@echo "  make format        - Format code with ruff"
	@echo "  make mypy          - Run mypy type checker"
	@echo "  make check         - Run all checks (lint, format, type, tests)"
	@echo "  make pre-push      - Run pre-push checks (lint, format, tests)"
	@echo "  make clean         - Clean build artifacts"
	@echo "  make run           - Run the application locally"
	@echo "  make docker-build  - Build Docker image"
	@echo "  make docker-up     - Start services with docker-compose"
	@echo "  make docker-down   - Stop services with docker-compose"
	@echo "  make docker-logs   - View docker-compose logs"
	@echo "  make migrate       - Create new migration"
	@echo "  make migrate-upgrade - Run database migrations"
	@echo "  make migrate-downgrade - Rollback last migration"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

test:
	pytest

lint:
	ruff check app tests

format:
	ruff format app tests

mypy:
	mypy app

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .mypy_cache .ruff_cache htmlcov/ .coverage
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

migrate:
	alembic revision --autogenerate -m "$(msg)"

migrate-upgrade:
	alembic upgrade head

migrate-downgrade:
	alembic downgrade -1

check: lint format mypy test
	@echo "✅ All checks passed!"

pre-push: lint format test
	@echo "✅ Pre-push checks passed! Ready to push."

