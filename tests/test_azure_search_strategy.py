
import asyncio
import json
import time
from typing import Callable, Dict, Tuple, Any, Optional

import pytest

from prompt_retrieval import (
    AzureAISearchConfig,
    AzureAISearchPromptStrategy,
    PromptRetrievalInput,
    QuestionInput,
)


class FakeResponse:
    def __init__(self, status_code: int, payload: Optional[Dict[str, Any]] = None, text: str = ""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


class FakeAsyncClient:
    response_provider: Callable[[str], Tuple[int, Optional[Dict[str, Any]], str]] = lambda text: (200, {"value": []}, "")
    delay_seconds: float = 0.0
    track_concurrency: bool = False
    current_concurrency: int = 0
    max_concurrency: int = 0

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url: str, headers: Dict[str, str], content: Any):
        if isinstance(content, (bytes, bytearray)):
            body = json.loads(content.decode("utf-8"))
        elif isinstance(content, str):
            body = json.loads(content)
        else:
            body = content

        try:
            question_text = body["vectorQueries"][0]["text"]
        except Exception:
            question_text = ""

        if self.track_concurrency:
            FakeAsyncClient.current_concurrency += 1
            FakeAsyncClient.max_concurrency = max(
                FakeAsyncClient.max_concurrency, FakeAsyncClient.current_concurrency
            )

        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)

        status_code, payload, text = FakeAsyncClient.response_provider(question_text)

        if self.track_concurrency:
            FakeAsyncClient.current_concurrency -= 1

        return FakeResponse(status_code=status_code, payload=payload, text=text)

    @classmethod
    def reset(cls):
        cls.response_provider = lambda text: (200, {"value": []}, "")
        cls.delay_seconds = 0.0
        cls.track_concurrency = False
        cls.current_concurrency = 0
        cls.max_concurrency = 0


@pytest.fixture(autouse=True)
def reset_fake_client(monkeypatch):
    FakeAsyncClient.reset()
    import httpx  # noqa
    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    yield
    FakeAsyncClient.reset()


def make_strategy(threshold: float = 0.75, max_parallel: int = 5) -> AzureAISearchPromptStrategy:
    cfg = AzureAISearchConfig(
        endpoint="https://fake.search.windows.net",
        api_key="fake-key",
        api_version="2024-07-01-preview",
        index_name="fake-index",
        similarity_threshold=threshold,
    )
    return AzureAISearchPromptStrategy(search_config=cfg, max_parallel_requests=max_parallel)


def mk_questions(n: int):
    return [QuestionInput(question_id=f"q{i+1}", question_text=f"Question text {i+1}") for i in range(n)]


@pytest.mark.asyncio
async def test_returns_same_number_of_results_as_questions():
    def provider(_text: str):
        return 200, {"value": []}, ""

    FakeAsyncClient.response_provider = provider

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
    def provider(text: str):
        payload = {
            "value": [
                {
                    "@search.score": 0.82,
                    "promptText": "Selected prompt for: " + text,
                    "questionText": text,
                    "questionId": "q1",
                }
            ]
        }
        return 200, payload, ""

    FakeAsyncClient.response_provider = provider

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
    def provider(text: str):
        payload = {
            "value": [
                {
                    "@search.score": 0.31,
                    "promptText": "Low-similarity prompt",
                    "questionText": text,
                    "questionId": "qX",
                }
            ]
        }
        return 200, payload, ""

    FakeAsyncClient.response_provider = provider

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
    def provider(_text: str):
        return 500, None, "Internal Server Error"

    FakeAsyncClient.response_provider = provider

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
    assert "Search error 500" in r.error


@pytest.mark.asyncio
async def test_concurrency_limit_max_5():
    FakeAsyncClient.delay_seconds = 0.05
    FakeAsyncClient.track_concurrency = True

    def provider(text: str):
        payload = {
            "value": [
                {
                    "@search.score": 0.9,
                    "promptText": f"Prompt for {text}",
                    "questionText": text,
                    "questionId": "id-" + (text[-1] if text else "x"),
                }
            ]
        }
        return 200, payload, ""

    FakeAsyncClient.response_provider = provider

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
    assert FakeAsyncClient.max_concurrency <= 5, f"Exceeded concurrency: {FakeAsyncClient.max_concurrency}"
    assert elapsed >= 0.08
