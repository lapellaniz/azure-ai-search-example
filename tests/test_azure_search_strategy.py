
import asyncio
import time
from collections.abc import Callable
from typing import Any
from unittest.mock import patch

import pytest
from azure.core.exceptions import HttpResponseError
from azure.search.documents.models import VectorizedQuery
from prompt_retrieval import (
    AzureAISearchConfig,
    PromptRetrievalInput,
    QuestionInput,
    SimilaritySearchPromptStrategy,
    TelemetryService,
)


class FakeSearchResult:
    def __init__(self, search_score: float, prompt_text: str, question_text: str, question_id: str):
        self.search_score = search_score
        self.prompt_text = prompt_text  
        self.question_text = question_text
        self.question_id = question_id

    def get(self, key, default=None):
        """Allow dict-style access for compatibility with Azure SDK"""
        if key == "@search.score":
            return self.search_score
        elif key == "promptText":
            return self.prompt_text
        elif key == "questionText": 
            return self.question_text
        elif key == "questionId":
            return self.question_id
        else:
            return default

    def __getitem__(self, key):
        """Allow dict-style access for compatibility"""
        result = self.get(key)
        if result is None:
            raise KeyError(f"Key '{key}' not found")
        return result


class FakeAsyncIterator:
    def __init__(self, items):
        self.items = items or []
        self.index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        return item


class FakeSearchClient:
    response_provider: Callable[[Any], tuple[bool, list[FakeSearchResult] | None, str | None]] = \
        lambda call_info: (True, [], None)
    delay_seconds: float = 0.0
    track_concurrency: bool = False
    current_concurrency: int = 0
    max_concurrency: int = 0
    call_count: int = 0

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def search(self, search_text: str = None, vector_queries: list[VectorizedQuery] = None, top: int = 1, **kwargs):
        # Increment call count and use it for provider
        FakeSearchClient.call_count += 1
        call_info = {
            'call_count': FakeSearchClient.call_count,
            'search_text': search_text,
            'vector_queries': vector_queries,
            'top': top,
            'kwargs': kwargs
        }

        if self.track_concurrency:
            FakeSearchClient.current_concurrency += 1
            FakeSearchClient.max_concurrency = max(
                FakeSearchClient.max_concurrency, FakeSearchClient.current_concurrency
            )

        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)

        success, results, error_msg = FakeSearchClient.response_provider(call_info)

        if self.track_concurrency:
            FakeSearchClient.current_concurrency -= 1

        if not success:
            raise HttpResponseError(message=error_msg or "Search error")

        return FakeAsyncIterator(results or [])

    @classmethod
    def reset(cls):
        cls.response_provider = lambda call_info: (True, [], None)
        cls.delay_seconds = 0.0
        cls.track_concurrency = False
        cls.current_concurrency = 0
        cls.max_concurrency = 0
        cls.call_count = 0


@pytest.fixture(autouse=True)
def mock_search_client():
    FakeSearchClient.reset()
    with patch('prompt_retrieval.strategies.similarity_search.strategy.SearchClient', FakeSearchClient):
        yield
    FakeSearchClient.reset()


def make_strategy(threshold: float = 0.75, max_parallel: int = 5) -> SimilaritySearchPromptStrategy:
    cfg = AzureAISearchConfig(
        endpoint="https://fake.search.windows.net",
        api_key="fake-key",
        api_version="2024-07-01-preview",
        index_name="fake-index",
        similarity_threshold=threshold,
    )
    # Use the mock telemetry service from conftest.py
    telemetry = TelemetryService(
        service_name="prompt-retrieval",
        service_version="0.1.0",
        enable_console_exporters_when_no_ai=False,  # Disable console exporters in tests
    )
    return SimilaritySearchPromptStrategy(search_config=cfg, telemetry=telemetry, max_parallel_requests=max_parallel)


def mk_questions(n: int):
    return [QuestionInput(question_id=f"q{i+1}", question_text=f"Question text {i+1}") for i in range(n)]


@pytest.mark.asyncio
async def test_returns_same_number_of_results_as_questions():
    def provider(_call_info):
        return True, [], None

    FakeSearchClient.response_provider = provider

    strategy = make_strategy()
    request = PromptRetrievalInput(
        assessment_template_id="asm-1",
        questions=mk_questions(5),
    )

    result = await strategy.retrieve_prompts(request)
    assert result.assessment_template_id == "asm-1"
    assert len(result.results) == 5
    assert all(not r.match_found for r in result.results)


@pytest.mark.asyncio
async def test_single_question_match_above_threshold():
    def provider(call_info):
        search_result = FakeSearchResult(
            search_score=0.82,
            prompt_text="Selected prompt for: How are you today?",
            question_text="How are you today?",
            question_id="q1"
        )
        return True, [search_result], None

    FakeSearchClient.response_provider = provider

    strategy = make_strategy(threshold=0.75)
    request = PromptRetrievalInput(
        assessment_template_id="asm-2",
        questions=[QuestionInput(question_id="q1", question_text="How are you today?")],
    )

    result = await strategy.retrieve_prompts(request)
    assert len(result.results) == 1
    r = result.results[0]
    assert r.match_found is True
    assert r.match_score == pytest.approx(0.82)
    assert isinstance(r.selected_prompt_text, str)
    assert "How are you today?" in r.selected_prompt_text


@pytest.mark.asyncio
async def test_single_question_below_threshold_no_match():
    def provider(call_info):
        search_result = FakeSearchResult(
            search_score=0.31,
            prompt_text="Low-similarity prompt",
            question_text="A low-similarity question",
            question_id="qX"
        )
        return True, [search_result], None

    FakeSearchClient.response_provider = provider

    strategy = make_strategy(threshold=0.75)
    request = PromptRetrievalInput(
        assessment_template_id="asm-3",
        questions=[QuestionInput(question_id="qX", question_text="A low-similarity question")],
    )

    result = await strategy.retrieve_prompts(request)
    assert len(result.results) == 1
    r = result.results[0]
    assert r.match_found is False
    assert r.match_score == pytest.approx(0.31)
    assert r.selected_prompt_text == "Low-similarity prompt"


@pytest.mark.asyncio
async def test_http_error_sets_error_and_no_match():
    def provider(_call_info):
        return False, None, "Internal Server Error"

    FakeSearchClient.response_provider = provider

    strategy = make_strategy(threshold=0.75)
    request = PromptRetrievalInput(
        assessment_template_id="asm-4",
        questions=[QuestionInput(question_id="qErr", question_text="Trigger server error")],
    )

    result = await strategy.retrieve_prompts(request)
    assert len(result.results) == 1
    r = result.results[0]
    assert r.match_found is False
    assert r.error is not None
    assert "HTTP error" in r.error


@pytest.mark.asyncio
async def test_concurrency_limit_max_5():
    FakeSearchClient.delay_seconds = 0.05
    FakeSearchClient.track_concurrency = True

    def provider(call_info):
        # Create different results based on call count to distinguish them
        call_count = call_info['call_count']
        search_result = FakeSearchResult(
            search_score=0.9,
            prompt_text=f"Prompt for call {call_count}",
            question_text=f"Question text {call_count}",
            question_id=f"id-{call_count}"
        )
        return True, [search_result], None

    FakeSearchClient.response_provider = provider

    strategy = make_strategy(threshold=0.5, max_parallel=5)

    questions = [QuestionInput(question_id=f"q{i}", question_text=f"Question text {i}") for i in range(12)]
    request = PromptRetrievalInput(
        assessment_template_id="asm-5",
        questions=questions,
    )

    start = time.perf_counter()
    result = await strategy.retrieve_prompts(request)
    elapsed = time.perf_counter() - start

    assert len(result.results) == 12
    assert all(r.match_found for r in result.results)
    assert FakeSearchClient.max_concurrency <= 5, f"Exceeded concurrency: {FakeSearchClient.max_concurrency}"
    assert elapsed >= 0.08
