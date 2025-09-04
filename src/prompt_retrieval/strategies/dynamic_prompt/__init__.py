"""
Dynamic prompt generation strategy.

This strategy uses AI models to dynamically generate prompts based on input questions.
It leverages large language models to create contextually relevant prompts for each question.
"""

from .config import DynamicPromptConfig
from .strategy import DynamicPromptStrategy

__all__ = [
    "DynamicPromptConfig",
    "DynamicPromptStrategy",
]
