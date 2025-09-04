"""
Configuration for prompt retrieval orchestrator.

This module contains configuration classes for orchestrating multiple prompt retrieval strategies.
"""

from dataclasses import dataclass


@dataclass
class OrchestratorConfig:
    """Configuration for orchestrating multiple prompt retrieval strategies."""
    
    # Orchestration settings
    enable_dynamic_prompt: bool = False
    similarity_threshold: float = 0.75  # Minimum score to consider a match
    max_parallel_requests: int = 5
    
    # Fallback behavior
    fallback_to_passthrough: bool = True
    fallback_to_dynamic: bool = False  # Only used if enable_dynamic_prompt is True
