"""
Similarity-based prompt search strategy.

This strategy searches for existing prompts by finding those with questions
most similar to the input question. It uses semantic similarity (vector search)
to match questions and return the corresponding prompts.
"""

from .config import AzureAISearchConfig, AzureOpenAIClientLike
from .strategy import SimilaritySearchPromptStrategy

__all__ = [
    "AzureAISearchConfig",
    "AzureOpenAIClientLike", 
    "SimilaritySearchPromptStrategy",
]
