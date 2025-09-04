"""
Passthrough prompt strategy.

This strategy uses input questions directly as prompts with optional formatting.
It's the simplest strategy that treats question text as prompt text with minimal transformation.
"""

from .config import PassthroughPromptConfig
from .strategy import PassthroughPromptStrategy

__all__ = [
    "PassthroughPromptConfig",
    "PassthroughPromptStrategy",
]
