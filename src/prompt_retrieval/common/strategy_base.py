
from __future__ import annotations

from typing import Protocol

from .models import PromptRetrievalInput, PromptRetrievalOutput


class PromptRetrievalStrategy(Protocol):
    async def retrieve_prompts(self, request: PromptRetrievalInput) -> PromptRetrievalOutput:
        ...
