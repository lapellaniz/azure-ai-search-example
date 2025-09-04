from __future__ import annotations

import asyncio

from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import AzureError, HttpResponseError
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import VectorizedQuery

from ...common import (
    PromptRetrievalInput,
    PromptRetrievalOutput,
    PromptRetrievalStrategy,
    QuestionInput,
    QuestionPromptMatch,
    TelemetryService,
)
from .config import AzureAISearchConfig, AzureOpenAIClientLike


class SimilaritySearchPromptStrategy(PromptRetrievalStrategy):
    """
    Finds existing prompts by semantic similarity using Azure AI Search vector search.
    Uses question text vectorization to match against a curated prompt library with configurable similarity thresholds.
    """
    def __init__(
        self,
        search_config: AzureAISearchConfig,
        telemetry: TelemetryService,
        azure_openai_client: AzureOpenAIClientLike | None = None,
        max_parallel_requests: int = 5,
    ) -> None:
        self._config = search_config
        self._logger = telemetry
        self._azure_openai_client = azure_openai_client
        self._semaphore = asyncio.Semaphore(max_parallel_requests)

        if not (
            self._config.endpoint
            and self._config.api_key
            and self._config.index_name
        ):
            raise ValueError("AzureAISearchConfig is missing required fields.")

        # Create Azure Search client
        credential = AzureKeyCredential(self._config.api_key)
        self._search_client = SearchClient(
            endpoint=self._config.endpoint,
            index_name=self._config.index_name,
            credential=credential,
        )

    async def retrieve_prompts(self, request: PromptRetrievalInput) -> PromptRetrievalOutput:
        self._logger.info(
            "Starting prompt retrieval for assessment_template_id=%s with %d questions",
            request.assessment_template_id,
            len(request.questions),
        )

        output = PromptRetrievalOutput(assessment_template_id=request.assessment_template_id)

        with self._logger.start_span(
            "retrieve_prompts",
            {"assessment_template_id": request.assessment_template_id, "question_count": len(request.questions)},
        ):
            tasks = [self._query_top1_for_question(q) for q in request.questions]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        for res in results:
            if isinstance(res, Exception):
                self._logger.exception("Unhandled exception during prompt retrieval: %s", res)
                continue
            output.results.append(res)

        matched = sum(1 for r in output.results if getattr(r, "match_found", False))
        self._logger.record_matched_questions(request.assessment_template_id, matched)

        self._logger.info(
            "Finished prompt retrieval for assessment_template_id=%s (matched=%d/%d)",
            request.assessment_template_id, matched, len(output.results)
        )

        return output

    async def _query_top1_for_question(self, q: QuestionInput) -> QuestionPromptMatch:
        async with self._semaphore:
            self._logger.debug("Querying Azure AI Search for question_id=%s", q.question_id)
            
            try:
                # Create vector query for semantic search
                vector_query = VectorizedQuery(
                    vector=None,  # Will be populated by the SDK when using text
                    k_nearest_neighbors=1,
                    fields="questionTextVector",
                    text=q.question_text,  # Let the SDK handle vectorization
                )

                # Perform the search
                results = await self._search_client.search(
                    search_text="",  # Empty for pure vector search
                    vector_queries=[vector_query],
                    select=["promptText", "questionText", "questionId"],
                    top=1,
                )

                # Convert async iterator to list
                search_results = []
                async for result in results:
                    search_results.append(result)

                if not search_results:
                    self._logger.info("No results for question_id=%s", q.question_id)
                    return QuestionPromptMatch(
                        question_id=q.question_id,
                        question_text=q.question_text,
                        match_found=False,
                    )

                # Process the first (and only) result
                doc = search_results[0]
                score = doc.get("@search.score")
                prompt_text = doc.get("promptText")
                result_question_text = doc.get("questionText")
                result_question_id = doc.get("questionId")

                match_found = False
                numeric_score: float | None = None
                if isinstance(score, (int, float)):
                    numeric_score = float(score)
                    match_found = numeric_score >= self._config.similarity_threshold
                else:
                    self._logger.warning(
                        "Missing score for question_id=%s; treating as no match.", q.question_id
                    )

                return QuestionPromptMatch(
                    question_id=result_question_id or q.question_id,
                    question_text=result_question_text or q.question_text,
                    match_found=match_found,
                    match_score=numeric_score,
                    selected_prompt_text=prompt_text,
                )

            except HttpResponseError as ex:
                error_msg = f"Azure Search HTTP error for question_id={q.question_id}: {ex.status_code} - {ex.message}"
                self._logger.error(error_msg)
                return QuestionPromptMatch(
                    question_id=q.question_id,
                    question_text=q.question_text,
                    match_found=False,
                    error=error_msg,
                )
            except AzureError as ex:
                error_msg = f"Azure Search error for question_id={q.question_id}: {ex}"
                self._logger.error(error_msg)
                return QuestionPromptMatch(
                    question_id=q.question_id,
                    question_text=q.question_text,
                    match_found=False,
                    error=error_msg,
                )
            except Exception as ex:  # pragma: no cover
                self._logger.exception("Exception querying question_id=%s: %s", q.question_id, ex)
                return QuestionPromptMatch(
                    question_id=q.question_id,
                    question_text=q.question_text,
                    match_found=False,
                    error=str(ex),
                )

    async def close(self):
        """Close the search client and cleanup resources."""
        if hasattr(self, '_search_client'):
            await self._search_client.close()
