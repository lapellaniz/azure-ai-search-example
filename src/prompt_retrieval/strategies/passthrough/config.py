"""
Configuration for passthrough prompt strategy.

This module contains configuration classes for direct question-to-prompt passthrough.
"""

from dataclasses import dataclass


@dataclass
class PassthroughPromptConfig:
    """Configuration for passthrough prompt strategy."""
    
    # Prompt formatting options
    prefix: str | None = None
    suffix: str | None = None
    format_template: str | None = None  # e.g., "Please answer: {question}"
    
    # Metadata settings
    include_question_id: bool = False
    include_metadata: bool = True
