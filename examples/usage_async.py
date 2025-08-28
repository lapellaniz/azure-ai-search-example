
import asyncio
import logging

from prompt_retrieval import (
    AzureAISearchConfig,
    AzureAISearchPromptStrategy,
    PromptRetrievalInput,
    QuestionInput,
)


async def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("prompt-retrieval")

    search_config = AzureAISearchConfig(
        endpoint="https://<your-search>.search.windows.net",
        api_key="<SEARCH-API-KEY>",
        api_version="2024-07-01-preview",
        index_name="<your-index>",
        similarity_threshold=0.25,
    )

    strategy = AzureAISearchPromptStrategy(
        search_config=search_config,
        logger=logger,
        azure_openai_client=None,
        max_parallel_requests=5,
        http_timeout_seconds=20.0,
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
