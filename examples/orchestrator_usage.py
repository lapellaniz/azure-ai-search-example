"""
Orchestrator Usage Example

This example demonstrates how to use the PromptRetrievalOrchestrator to coordinate
multiple prompt retrieval strategies with intelligent fallback handling.
"""

import asyncio
import logging
import os

from dotenv import load_dotenv
from prompt_retrieval import (
    # Strategy configs
    AzureAISearchConfig,
    DynamicPromptConfig,
    # Orchestrator
    OrchestratorConfig,
    PassthroughPromptConfig,
    PromptRetrievalInput,
    PromptRetrievalOrchestrator,
    # Common models
    QuestionInput,
    TelemetryService,
)


async def main():
    """Demonstrate orchestrator usage with fallback strategies."""
    
    # Load environment variables
    load_dotenv()
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize telemetry
    telemetry = TelemetryService(
        service_name="orchestrator-example",
        service_version="1.0.0"
    )

    # Configure similarity search strategy
    similarity_config = AzureAISearchConfig(
        endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
        api_key=os.getenv("AZURE_SEARCH_API_KEY"),
        api_version=os.getenv("AZURE_SEARCH_API_VERSION"),
        index_name=os.getenv("SEARCH_INDEX_NAME_QUESTIONS"),
        similarity_threshold=float(os.getenv("SEARCH_SIMILARITY_THRESHOLD", 0.75)),
    )
    
    # Configure passthrough strategy (with custom formatting)
    passthrough_config = PassthroughPromptConfig(
        format_template="Please provide a comprehensive answer to: {question}",
        prefix="[Fallback]",
        include_metadata=True
    )
    
    # Configure dynamic prompt strategy (optional)
    dynamic_config = DynamicPromptConfig(
        endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
        model_name=os.getenv("AZURE_OPENAI_MODEL_NAME", "gpt-4"),
        temperature=0.7,
        system_prompt="Generate helpful prompts for healthcare assessment questions."
    )
    
    # Configure orchestrator
    orchestrator_config = OrchestratorConfig(
        similarity_search_config=similarity_config,
        passthrough_config=passthrough_config,
        dynamic_prompt_config=dynamic_config,
        enable_dynamic_prompt=False,  # Set to True to enable dynamic prompts
        similarity_threshold=0.8,  # Higher threshold for better quality matches
        fallback_to_passthrough=True,
        fallback_to_dynamic=False,  # Only used if enable_dynamic_prompt=True
        max_parallel_requests=3
    )
    
    # Create orchestrator
    orchestrator = PromptRetrievalOrchestrator(
        config=orchestrator_config,
        telemetry=telemetry
    )

    # Example questions - mix of potentially matchable and unmatchable
    request = PromptRetrievalInput(
        assessment_template_id="assessment-123",
        questions=[
            QuestionInput(question_id="q1", question_text="How often do you exercise each week?"),
            QuestionInput(question_id="q2", question_text="Do you have any dietary restrictions?"),
            QuestionInput(question_id="q3", question_text="What is your favorite color of unicorn?"),  # Unlikely to match
            QuestionInput(question_id="q4", question_text="Describe your sleep patterns."),
            QuestionInput(question_id="q5", question_text="How many dragons have you seen today?"),  # Unlikely to match
        ]
    )

    # Retrieve prompts using orchestrator
    print("\\nStarting orchestrated prompt retrieval...")
    result = await orchestrator.retrieve_prompts(request)
    
    print(f"\\nRetrieved prompts for assessment: {result.assessment_template_id}")
    print(f"Total matches found: {len(result.results)}")
    
    # Display results
    for match in result.results:
        print(f"\\n--- Question {match.question_id} ---")
        print(f"Question: {match.question_text}")
        print(f"Prompt: {match.selected_prompt_text}")
        print(f"Match Score: {match.match_score:.3f}")
        print(f"Match Found: {match.match_found}")
        if match.error:
            print(f"Error: {match.error}")


if __name__ == "__main__":
    asyncio.run(main())
