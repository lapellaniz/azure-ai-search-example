
# Prompt Retrieval Framework

A modular, async prompt retrieval framework supporting multiple strategies including Azure AI Search with vector queries, GPT-based prompt generation, and direct question-based retrieval.

## Architecture

The framework provides a common interface (`PromptRetrievalStrategy`) that all strategy implementations follow for consistency. This allows you to easily switch between different retrieval methods or use multiple strategies together.

### Available Strategies

- **Azure Search Strategy**: Uses Azure AI Search with vector queries for semantic similarity matching
- **GPT Prompt Strategy**: _(Coming Soon)_ Uses GPT models to generate prompts based on questions  
- **Question Strategy**: _(Coming Soon)_ Direct question-based retrieval from predefined prompt databases

## Prerequisites

- Python 3.12+
- [Poetry](https://python-poetry.org/) for dependency management

## Installation

### Install Poetry (if not already installed)
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### Install project dependencies
```bash
# Install all dependencies (including dev dependencies)
poetry install

# Or use the Makefile
make install
```

## Development Workflow

### Common Commands

#### Using Make (Recommended)
```bash
# Install dependencies
make install

# Run tests
make test

# Run example
make example

# Build package
make build

# Lint code
make lint

# Format code (with Ruff and Black)
make fmt

# Clean build artifacts
make clean

# Full CI pipeline (install + test)
make ci

# Get help
make help
```

#### Using Poetry Directly
```bash
# Install dependencies
poetry install

# Run tests
poetry run pytest

# Run specific test file
poetry run pytest tests/test_azure_search_strategy.py

# Run example
poetry run python -m examples.usage_async

# Add new dependency
poetry add package-name

# Add development dependency
poetry add --group dev package-name

# Add test dependency
poetry add --group test package-name

# Update dependencies
poetry update

# Show dependency tree
poetry show --tree

# Build package
poetry build

# Activate virtual environment
poetry shell

# Run any command in the virtual environment
poetry run python script.py
```

## Virtual Environment Management

Poetry automatically manages virtual environments for you:

```bash
# Activate the virtual environment
poetry shell

# Run commands without activating
poetry run <command>

# Show virtual environment info
poetry env info

# Show virtual environment path
poetry env info --path
```

## Dependency Management

### Adding Dependencies
```bash
# Production dependency
poetry add httpx

# Development dependency (linting, formatting, etc.)
poetry add --group dev black ruff

# Test dependency
poetry add --group test pytest pytest-asyncio

# Specific version
poetry add "httpx>=0.27.0"
```

### Removing Dependencies
```bash
poetry remove package-name
poetry remove --group dev package-name
```

## Dev Containers (VS Code)

This repo ships a Compose-based dev container that includes **Azure CLI** and **Docker + Compose v2** tools.

**Prereqs**: Docker Desktop (Linux containers) and the VS Code **Dev Containers** extension.

**Use it**:
1. Open the folder in VS Code.
2. Press `F1` → **Dev Containers: Reopen in Container**.
3. First boot will install Poetry, create virtual environment, and install dependencies.

Inside the container:
```bash
az version
docker version
docker compose version
poetry --version
make test
```

## Project Structure

```
src/
├── prompt_retrieval/              # Main package
│   ├── __init__.py               # Public API exports
│   ├── common/                   # Shared components
│   │   ├── __init__.py
│   │   ├── models.py            # Common data models
│   │   ├── strategy_base.py     # Base strategy interface
│   │   └── telemetry.py         # Telemetry service
│   └── strategies/              # Strategy implementations
│       ├── __init__.py
│       ├── azure_search/        # Azure AI Search strategy
│       │   ├── __init__.py
│       │   ├── config.py        # Azure Search configuration
│       │   └── strategy.py      # Implementation
│       ├── dynamic_prompt/      # Dynamic prompt generation (future)
│       │   └── __init__.py
│       └── passthrough/         # Direct question-to-prompt passthrough (future)
│           └── __init__.py
└── experimentation/             # Experimentation utilities
    └── __init__.py

tests/                           # Test files
├── conftest.py                 # Shared test configuration
├── test_azure_search_strategy.py
└── test_telemetry_service.py

examples/                        # Usage examples
└── usage_async.py
```

## Usage

### Basic Usage

```python
import asyncio
from prompt_retrieval import (
    AzureAISearchConfig,
    SimilaritySearchPromptStrategy,
    QuestionInput,
    PromptRetrievalInput,
    TelemetryService,
)

async def main():
    # Configure telemetry
    telemetry = TelemetryService(
        service_name="my-app",
        service_version="1.0.0",
    )

    # Configure Azure Search strategy
    search_config = AzureAISearchConfig(
        endpoint="https://your-search.search.windows.net",
        api_key="your-api-key",
        api_version="2024-07-01-preview",
        index_name="your-index",
        similarity_threshold=0.75,
    )

    # Create strategy instance
    strategy = SimilaritySearchPromptStrategy(
        search_config=config,
        telemetry=telemetry
    )

    # Prepare request
    request = PromptRetrievalInput(
        assessment_template_id="assessment-123",
        questions=[
            QuestionInput(question_id="q1", question_text="How often do you exercise?"),
            QuestionInput(question_id="q2", question_text="Do you have dietary restrictions?"),
        ],
    )

    # Retrieve prompts
    result = await strategy.retrieve_prompts(request)
    
    # Process results
    for r in result.results:
        print(f"Question {r.question_id}: Match={r.match_found}, Score={r.match_score}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Adding New Strategies

To add a new strategy:

1. Create a new directory under `src/prompt_retrieval/strategies/your_strategy/`
2. Implement your strategy class inheriting from `PromptRetrievalStrategy`
3. Create configuration classes as needed
4. Export your strategy from the module's `__init__.py`
5. Add imports to the main `strategies/__init__.py`

Example structure:
```
strategies/
└── your_strategy/
    ├── __init__.py      # Export strategy and config
    ├── config.py        # Strategy-specific configuration
    └── strategy.py      # Strategy implementation
```

## Configuration

Dependencies are managed in `pyproject.toml` with Poetry format:

- **Production dependencies**: `[tool.poetry.dependencies]`
- **Development dependencies**: `[tool.poetry.group.dev.dependencies]`
- **Test dependencies**: `[tool.poetry.group.test.dependencies]`

## Building and Publishing

```bash
# Build wheel and source distribution
poetry build

# Check package
poetry check

# Publish to PyPI (configure credentials first)
poetry publish
```
