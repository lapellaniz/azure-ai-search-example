
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class AzureAISearchConfig:
    endpoint: str
    api_key: str
    api_version: str
    index_name: str
    similarity_threshold: float = 0.2


class AzureOpenAIClientLike(Protocol):
    def __getattr__(self, item): ...  # pragma: no cover
