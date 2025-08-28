
# Azure AI Prompt Retrieval (Python)

A production-ready async strategy for retrieving top-1 prompts from **Azure AI Search** using vector queries.

## Features

- Dataclasses for input/output models
- Strategy pattern with a concrete Azure AI Search implementation
- Async I/O via `httpx` with **configurable concurrency (default 5)**
- Dependency injection for config, logger, and optional Azure OpenAI client
- Pytest unit tests with a fake async HTTP client (no network calls)
- VS Code configuration for testing

## Project Layout

```text
azure_ai_prompt_retrieval/
├─ src/
│  └─ prompt_retrieval/
│     ├─ __init__.py
│     ├─ models.py
│     ├─ config.py
│     ├─ strategy_base.py
│     └─ azure_search_strategy.py
├─ tests/
│  └─ test_azure_search_strategy.py
├─ examples/
│  └─ usage_async.py
├─ .vscode/
│  ├─ settings.json
│  ├─ launch.json
│  └─ extensions.json
├─ requirements.txt
├─ pytest.ini
└─ README.md
```

## Quickstart (VS Code)

1. **Create & Activate venv**
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS/Linux
   source .venv/bin/activate
   ```
2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
3. **Run tests**
   ```bash
   pytest
   ```
4. **Try the example**
   ```bash
   python -m examples.usage_async
   ```

## Configuration

Supply your Azure AI Search details in code via `AzureAISearchConfig`:

```python
from prompt_retrieval import AzureAISearchConfig

cfg = AzureAISearchConfig(
    endpoint="https://<your-search>.search.windows.net",
    api_key="<SEARCH-API-KEY>",
    api_version="2024-07-01-preview",
    index_name="<your-index>",
    similarity_threshold=0.25,
)
```

## Notes

- The strategy uses `vectorQueries` with `kind="text"` against `questionTextVector` and selects `promptText,questionText,questionId`.
- Ensure your Azure AI Search index supports vector search and is configured with a compatible vectorizer.
- Concurrency is capped with a semaphore (default **5**). Adjust via `max_parallel_requests`.
