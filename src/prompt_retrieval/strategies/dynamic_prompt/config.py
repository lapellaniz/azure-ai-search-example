"""
Configuration for dynamic prompt generation strategy.

This module contains configuration classes for AI-powered prompt generation.
"""

from dataclasses import dataclass


@dataclass
class DynamicPromptConfig:
    """Configuration for dynamic prompt generation using AI models."""
    
    # OpenAI/Azure OpenAI configuration
    endpoint: str
    api_key: str
    api_version: str = "2024-02-01"
    model_name: str = "gpt-4"
    
    # Generation parameters
    max_tokens: int | None = 500
    temperature: float = 0.7
    
    # Prompt engineering settings
    system_prompt: str | None = None
    prompt_template: str | None = None
