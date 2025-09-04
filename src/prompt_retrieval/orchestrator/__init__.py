"""
Prompt retrieval orchestrator module.

This module provides an orchestrator that coordinates multiple prompt retrieval strategies
to provide the best possible results. It implements a fallback chain:

1. Similarity search (primary strategy)
2. Passthrough (fallback for unmatched questions)  
3. Dynamic prompt generation (optional, flag-controlled)

The orchestrator ensures that all questions receive some form of prompt,
using the most appropriate strategy available.
"""

from .config import OrchestratorConfig
from .orchestrator import PromptRetrievalOrchestrator

__all__ = [
    "OrchestratorConfig",
    "PromptRetrievalOrchestrator",
]
