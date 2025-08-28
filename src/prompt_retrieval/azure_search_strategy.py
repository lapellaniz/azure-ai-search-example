from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Optional
from urllib import request

import httpx

from .config import AzureAISearchConfig, AzureOpenAIClientLike
from .models import (
    PromptRetrievalInput,
    PromptRetrievalOutput,
    QuestionInput,
    QuestionPromptMatch,
)
from .strategy_base import PromptRetrievalStrategy
from .telemetry import TelemetryService  

class AzureAISearchPromptStrategy(PromptRetrievalStrategy):
    def __init__(
        self,
        search_config: AzureAISearchConfig,
        telemetry: TelemetryService,
        azure_openai_client: Optional[AzureOpenAIClientLike] = None,
        max_parallel_requests: int = 5,
        http_timeout_seconds: float = 15.0,
    ) -> None:
        self._config = search_config
        self._logger = telemetry
        self._azure_openai_client = azure_openai_client
        self._semaphore = asyncio.Semaphore(max_parallel_requests)
        self._http_timeout = http_timeout_seconds

        self._search_url = (
            f"{self._config.endpoint}/indexes/{self._config.index_name}/docs/search"
            f"?api-version={self._config.api_version}"
        )

        if not (
            self._config.endpoint
            and self._config.api_key
            and self._config.index_name
            and self._config.api_version
        ):
            raise ValueError("AzureAISearchConfig is missing required fields.")

    async def retrieve_prompts(self, request: PromptRetrievalInput) -> PromptRetrievalOutput:
        self._logger.info(
            "Starting prompt retrieval for assessment_template_id=%s with %d questions",
            request.assessment_template_id,
            len(request.questions),
        )

        output = PromptRetrievalOutput(assessment_template_id=request.assessment_template_id)

        async with httpx.AsyncClient(timeout=self._http_timeout) as client:            
            with self._logger.start_span(
                "retrieve_prompts",
                {"assessment_template_id": request.assessment_template_id, "question_count": len(request.questions)},
            ):
                tasks = [self._query_top1_for_question(client, q) for q in request.questions]
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

    async def _query_top1_for_question(
        self, client: httpx.AsyncClient, q: QuestionInput
    ) -> QuestionPromptMatch:
        async with self._semaphore:
            self._logger.debug("Querying Azure AI Search for question_id=%s", q.question_id)
            body: Dict[str, Any] = {
                "vectorQueries": [
                    {
                        "kind": "text",
                        "text": q.question_text,
                        "k": 1,
                        "fields": "questionTextVector",
                    }
                ],
                "select": "promptText,questionText,questionId",
                "top": 1,
            }

            headers = {
                "Content-Type": "application/json",
                "api-key": self._config.api_key,
            }

            try:
                resp = await client.post(
                    self._search_url, headers=headers, content=json.dumps(body)
                )
                if resp.status_code >= 400:
                    msg = f"Search error {resp.status_code} for question_id={q.question_id}: {resp.text}"
                    self._logger.error(msg)
                    return QuestionPromptMatch(
                        question_id=q.question_id,
                        question_text=q.question_text,
                        match_found=False,
                        error=msg,
                    )

                payload = resp.json()
                docs = payload.get("value", [])
                if not docs:
                    self._logger.info("No results for question_id=%s", q.question_id)
                    return QuestionPromptMatch(
                        question_id=q.question_id,
                        question_text=q.question_text,
                        match_found=False,
                    )

                doc = docs[0]
                score = doc.get("@search.score") or doc.get("score")
                prompt_text = doc.get("promptText")
                result_question_text = doc.get("questionText")
                result_question_id = doc.get("questionId")

                match_found = False
                numeric_score: Optional[float] = None
                if isinstance(score, (int, float)):
                    numeric_score = float(score)
                    match_found = numeric_score >= self._config.similarity_threshold
                else:
                    self._logger.warning(
                        "Missing score for question_id=%s; treating as no match.", q.question_id
                    )

                return QuestionPromptMatch(
                    question_id=result_question_id,
                    question_text=result_question_text,
                    match_found=match_found,
                    match_score=numeric_score,
                    selected_prompt_text=prompt_text,
                )

            except Exception as ex:  # pragma: no cover
                self._logger.exception("Exception querying question_id=%s: %s", q.question_id, ex)
                return QuestionPromptMatch(
                    question_id=q.question_id,
                    question_text=q.question_text,
                    match_found=False,
                    error=str(ex),
                )
