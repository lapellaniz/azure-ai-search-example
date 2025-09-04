# Makefile for azure_ai_prompt_retrieval (Poetry-based)

# Check if Poetry is installed
POETRY := $(shell command -v poetry 2> /dev/null)

.PHONY: help install test example clean build ci lint fmt format activate check-poetry

help:
	@echo "Common commands:"
	@echo "  make install   - Install dependencies using Poetry"
	@echo "  make test      - Run pytest"
	@echo "  make example   - Run examples/usage_async.py"
	@echo "  make build     - Build wheel and sdist using Poetry"
	@echo "  make clean     - Remove caches and build artifacts"
	@echo "  make ci        - Full pipeline: install + test"
	@echo "  make lint      - Run linting with Ruff"
	@echo "  make fmt       - Format code with Ruff and Black"
	@echo "  make activate  - Show instructions to activate the virtual environment"

check-poetry:
ifndef POETRY
	$(error Poetry is not installed. Install it with: curl -sSL https://install.python-poetry.org | python3 -)
endif

install: check-poetry
	poetry install

test: install
	poetry run pytest -q

example: install
	poetry run python -m examples.usage_async

build: install
	poetry build

clean:
	@echo "Cleaning Python caches and build artifacts..."
	@rm -rf .pytest_cache __pycache__ .mypy_cache .ruff_cache
	@rm -rf dist build *.egg-info
	@find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true

ci: install test

# Lint with Ruff
lint: install
	poetry run ruff check src tests examples

# Format: Ruff (fix) then Black
fmt: install
	poetry run ruff check --fix src tests examples
	poetry run black src tests examples

format: fmt

activate:
	@echo "To activate the virtual environment:"
	@echo ""
	@echo "  poetry shell"
	@echo ""
	@echo "Or run commands with 'poetry run <command>'"

zip:
	@echo "Zipping project into project.zip..."
ifeq ($(OS),Windows_NT)
	powershell -Command "Compress-Archive -Path * -DestinationPath project.zip -Force"
else
	zip -r project.zip . -x '*.venv*' '*.git*' '__pycache__*' 'dist/*' 'build/*'
endif
