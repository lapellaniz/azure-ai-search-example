
"""
Async Usage Example

This example demonstrates how to use the SimilaritySearchPromptStrategy to retrieve
prompts based on questions using Azure AI Search with vector similarity.
"""

import asyncio
import logging
import os

from dotenv import load_dotenv

load_dotenv()

from prompt_retrieval import (
    AzureAISearchConfig,
    PromptRetrievalInput,
    QuestionInput,
    SimilaritySearchPromptStrategy,
    TelemetryService,
)


async def main():
    logging.basicConfig(level=logging.INFO)

    # Check for required environment variables
    required_env_vars = [
        "AZURE_SEARCH_ENDPOINT",
        "AZURE_SEARCH_API_KEY", 
        "AZURE_SEARCH_API_VERSION",
        "SEARCH_INDEX_NAME_QUESTIONS"
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        print(f"Missing required environment variables: {missing_vars}")
        print("Please create a .env file based on .env.example")
        return

    telemetry = TelemetryService(
        service_name="prompt-retrieval",
        service_version="0.1.0",
    )


    search_config = AzureAISearchConfig(
        endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
        api_key=os.getenv("AZURE_SEARCH_API_KEY"),
        api_version=os.getenv("AZURE_SEARCH_API_VERSION"),
        index_name=os.getenv("SEARCH_INDEX_NAME_QUESTIONS"),
        similarity_threshold=float(os.getenv("SEARCH_SIMILARITY_THRESHOLD", 0.75)),
    )

    strategy = SimilaritySearchPromptStrategy(
        search_config=search_config,
        telemetry=telemetry
    )

    request = PromptRetrievalInput(
        assessment_template_id="assessment-123",
        questions=[
            QuestionInput(question_id="q1", question_text="How often do you exercise each week?"),
            QuestionInput(question_id="q2", question_text="Do you have any dietary restrictions?"),
            QuestionInput(question_id="q3", question_text="Describe your current stress level."),
        ],
    )

    result = await strategy.retrieve_prompts(request)

    print(f"Assessment Template: {result.assessment_template_id}")
    for r in result.results:
        print(
            f"QuestionId={r.question_id} | Found={r.match_found} | Score={r.match_score} | "
            f"SelectedPromptText={repr(r.selected_prompt_text)[:80]} | Error={r.error}"
        )


if __name__ == "__main__":
    asyncio.run(main())
