"""
Prompt retrieval strategies package.

This package contains different implementations of prompt retrieval strategies:
- similarity_search: Finds existing prompts with similar questions using semantic search
- dynamic_prompt: Uses AI models to dynamically generate prompts for questions
- passthrough: Uses input questions directly as prompts (with optional formatting)
"""

from .dynamic_prompt import DynamicPromptConfig, DynamicPromptStrategy
from .passthrough import PassthroughPromptConfig, PassthroughPromptStrategy
from .similarity_search import AzureAISearchConfig, SimilaritySearchPromptStrategy

__all__ = [
    # Similarity search strategy
    "AzureAISearchConfig",
    "SimilaritySearchPromptStrategy",
    # Dynamic prompt strategy
    "DynamicPromptConfig", 
    "DynamicPromptStrategy",
    # Passthrough strategy
    "PassthroughPromptConfig",
    "PassthroughPromptStrategy",
]
