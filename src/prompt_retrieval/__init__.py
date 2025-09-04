
"""
Prompt Retrieval Package

A modular system for retrieving prompts using different strategies such as:
- Similarity search using semantic vectors (currently Azure AI Search)
- Dynamic prompt generation using AI models (future implementation)
- Direct passthrough of questions as prompts (future implementation)

The package also provides an orchestrator that coordinates multiple strategies
to ensure optimal prompt retrieval with intelligent fallback handling.

The package provides a common interface through PromptRetrievalStrategy that
all implementations follow for consistency.

Dependency injection is provided through the dependency-injector package,
enabling clean separation of concerns and enhanced testability.
"""

# Common interfaces and models
from .common import (
    PromptRetrievalInput,
    PromptRetrievalOutput,
    PromptRetrievalStrategy,
    QuestionInput,
    QuestionPromptMatch,
    TelemetryService,
)

# Orchestrator
from .orchestrator import (
    OrchestratorConfig,
    PromptRetrievalOrchestrator,
)

# Strategy implementations
from .strategies import (
    # Similarity search strategy
    AzureAISearchConfig,
    # Dynamic prompt strategy
    DynamicPromptConfig,
    DynamicPromptStrategy,
    # Passthrough strategy
    PassthroughPromptConfig,
    PassthroughPromptStrategy,
    SimilaritySearchPromptStrategy,
)

# Dependency injection
from .container import ApplicationContainer, create_container
from .services import get_container, get_orchestrator, reset_container

__all__ = [
    # Common models and interfaces
    "QuestionInput",
    "PromptRetrievalInput",
    "QuestionPromptMatch",
    "PromptRetrievalOutput",
    "PromptRetrievalStrategy",
    "TelemetryService",
    # Similarity search strategy
    "AzureAISearchConfig",
    "SimilaritySearchPromptStrategy",
    # Dynamic prompt strategy
    "DynamicPromptConfig",
    "DynamicPromptStrategy", 
    # Passthrough strategy
    "PassthroughPromptConfig",
    "PassthroughPromptStrategy",
    # Orchestrator
    "OrchestratorConfig",
    "PromptRetrievalOrchestrator",
    # Dependency injection
    "ApplicationContainer",
    "create_container",
    "get_container",
    "get_orchestrator",
    "reset_container",
]
