# Makefile for azure_ai_prompt_retrieval

VENV ?= .venv

ifeq ($(OS),Windows_NT)
  PY := $(VENV)/Scripts/python.exe
  PIP := $(VENV)/Scripts/pip.exe
else
  PY := $(VENV)/bin/python
  PIP := $(VENV)/bin/pip
endif

.PHONY: help venv install test example clean build ci lint fmt format activate

help:
	@echo "Common commands:"
	@echo "  make venv      - Create virtual environment (.venv)"
	@echo "  make install   - Install dependencies + package (editable)"
	@echo "  make test      - Run pytest"
	@echo "  make example   - Run examples/usage_async.py"
	@echo "  make build     - Build wheel and sdist"
	@echo "  make clean     - Remove caches and build artifacts"
	@echo "  make ci    	- Full pipeline: install + test"
	@echo "  make activate  - Show instructions to activate the virtual environment"

venv:
	python -m venv $(VENV)

install: venv
	$(PIP) install -r requirements.txt
	$(PIP) install -e .

# ensure the package is importable before tests
test: install
	$(PY) -m pytest -q

example:
	$(PY) -m examples.usage_async

build: install
	$(PIP) install build
	$(PY) -m build

# clean:
# 	rm -rf .pytest_cache __pycache__ .mypy_cache .ruff_cache
# 	rm -rf dist build *.egg-info
# 	-find src -name '__pycache__' -type d -exec rm -rf {} + 2>nul || true
# 	-find tests -name '__pycache__' -type d -exec rm -rf {} + 2>nul || true

clean:
	@echo Cleaning Python caches and build artifacts...
	@if exist .pytest_cache rmdir /s /q .pytest_cache
	@if exist build rmdir /s /q build
	@if exist dist rmdir /s /q dist
	@if exist *.egg-info rmdir /s /q *.egg-info
	@for /d /r %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"


ci: install test

# Lint with Ruff
lint:
	$(PY) -m ruff check src tests examples

# Format: Ruff (fix) then Black
fmt:
	$(PY) -m ruff check --fix src tests examples
	$(PY) -m black src tests examples

format: fmt

activate:
	@echo "To activate the virtual environment:"
	@echo ""
	@echo "  Windows:"
	@echo "	.venv\\Scripts\\activate"
	@echo ""
	@echo "  macOS/Linux:"
	@echo "    source .venv/bin/activate"

zip:
	@echo "Zipping project into project.zip..."
ifeq ($(OS),Windows_NT)
	powershell -Command "Compress-Archive -Path * -DestinationPath project.zip -Force" || $(PY) -c "import shutil; shutil.make_archive('project', 'zip', '.')"
else
	zip -r project.zip . -x '*.venv*' '*.git*' '__pycache__*'
endif
