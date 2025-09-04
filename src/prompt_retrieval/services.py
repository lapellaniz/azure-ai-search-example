"""
Convenience functions for dependency injection.

This module provides simple functions to get commonly used services
without needing to understand the full dependency injection setup.
"""

import os
from typing import Optional

from dependency_injector import containers
from prompt_retrieval.container import create_container
from prompt_retrieval.orchestrator.orchestrator import PromptRetrievalOrchestrator


# Global container instance
_container: Optional[containers.DynamicContainer] = None


def get_container() -> containers.DynamicContainer:
    """
    Get the global application container, creating it if necessary.
    
    Returns:
        DynamicContainer: The configured container
    """
    global _container
    if _container is None:
        _container = create_container()
    return _container


def get_orchestrator() -> PromptRetrievalOrchestrator:
    """
    Get a configured orchestrator with all dependencies injected.
    
    Returns:
        PromptRetrievalOrchestrator: Fully configured orchestrator
        
    Raises:
        ValueError: If required configuration is missing
    """
    container = get_container()
    
    # Validate required configuration
    required_vars = [
        "AZURE_SEARCH_ENDPOINT",
        "AZURE_SEARCH_API_KEY", 
        "AZURE_SEARCH_INDEX_NAME"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(
            f"Required environment variables not set: {', '.join(missing_vars)}"
        )
    
    return container.orchestrator()


def reset_container() -> None:
    """
    Reset the global container (useful for testing).
    """
    global _container
    _container = None