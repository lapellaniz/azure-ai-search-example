# Prompt Retrieval Orchestrator

The `PromptRetrievalOrchestrator` coordinates multiple prompt retrieval strategies to provide the best possible results with intelligent fallback handling.

## Strategy Flow

The orchestrator implements a three-tier fallback system:

1. **Similarity Search** (Primary)
   - Uses semantic similarity to find existing prompts with similar questions
   - Only accepts matches above the configured threshold
   - Fast and accurate for common questions

2. **Passthrough** (Fallback)
   - Uses input questions directly as prompts with optional formatting
   - Always succeeds for any input
   - Reliable fallback for unmatched questions

3. **Dynamic Prompt** (Optional)
   - AI-powered prompt generation using language models
   - Requires configuration and API access
   - Enabled via `enable_dynamic_prompt` flag

## Configuration

```python
from prompt_retrieval import (
    OrchestratorConfig,
    PromptRetrievalOrchestrator,
    AzureAISearchConfig,
    PassthroughPromptConfig,
    DynamicPromptConfig,
    TelemetryService,
)

# Configure strategies
similarity_config = AzureAISearchConfig(
    endpoint="https://your-search.search.windows.net",
    api_key="your-api-key",
    api_version="2023-11-01",
    index_name="your-index",
)

passthrough_config = PassthroughPromptConfig(
    format_template="Please answer: {question}",
    prefix="[Fallback]"
)

# Configure orchestrator
config = OrchestratorConfig(
    similarity_search_config=similarity_config,
    passthrough_config=passthrough_config,
    enable_dynamic_prompt=False,  # Set to True to enable AI generation
    similarity_threshold=0.8,     # Higher = more selective matching
    fallback_to_passthrough=True,
    max_parallel_requests=5
)

# Create orchestrator
telemetry = TelemetryService("my-app", "1.0.0")
orchestrator = PromptRetrievalOrchestrator(config, telemetry)
```

## Usage

```python
import asyncio
from prompt_retrieval import PromptRetrievalInput, QuestionInput

async def main():
    request = PromptRetrievalInput(
        assessment_template_id="assessment-123",
        questions=[
            QuestionInput("q1", "How often do you exercise?"),
            QuestionInput("q2", "What is your favorite mythical creature?"),  # Unlikely to match
        ]
    )
    
    result = await orchestrator.retrieve_prompts(request)
    
    for match in result.results:
        print(f"Question: {match.question_text}")
        print(f"Prompt: {match.selected_prompt_text}")
        print(f"Score: {match.match_score}")
        print(f"Found: {match.match_found}")
        print("---")

asyncio.run(main())
```

## Key Features

- **Intelligent Fallback**: Automatically handles unmatched questions
- **Configurable Thresholds**: Control quality vs coverage trade-offs
- **Parallel Processing**: Efficient concurrent request handling
- **Comprehensive Logging**: Built-in telemetry and monitoring
- **Extensible Design**: Easy to add new strategies

## Performance Considerations

- **Similarity Threshold**: Higher values (0.8+) prefer quality over coverage
- **Max Parallel Requests**: Tune based on downstream service limits
- **Fallback Strategy**: Passthrough is fast but basic; dynamic prompts are powerful but slower
- **Error Handling**: Individual strategy failures don't break the entire pipeline
