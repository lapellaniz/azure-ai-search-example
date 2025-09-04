"""
Dependency injection container for the prompt retrieval framework.

This module defines the main dependency injection container using dependency-injector
that wires together all services, strategies, and configurations.
"""

import os
from dependency_injector import containers, providers

from prompt_retrieval.common.telemetry import TelemetryService
from prompt_retrieval.strategies.similarity_search.config import AzureAISearchConfig
from prompt_retrieval.strategies.similarity_search.strategy import SimilaritySearchPromptStrategy
from prompt_retrieval.strategies.passthrough.config import PassthroughPromptConfig
from prompt_retrieval.strategies.passthrough.strategy import PassthroughPromptStrategy
from prompt_retrieval.strategies.dynamic_prompt.config import DynamicPromptConfig
from prompt_retrieval.strategies.dynamic_prompt.strategy import DynamicPromptStrategy
from prompt_retrieval.orchestrator.config import OrchestratorConfig
from prompt_retrieval.orchestrator.orchestrator import PromptRetrievalOrchestrator


class ApplicationContainer(containers.DeclarativeContainer):
    """Main application container for dependency injection."""

    # Configuration providers (singletons for sharing config across services)
    config = providers.Configuration()

    # Telemetry service - singleton for sharing across all strategies
    telemetry = providers.Singleton(
        TelemetryService,
        service_name=config.telemetry.service_name,
        service_version=config.telemetry.service_version,
    )

    # Configuration objects - singletons for efficiency
    azure_search_config = providers.Singleton(
        AzureAISearchConfig,
        endpoint=config.azure_search.endpoint,
        api_key=config.azure_search.api_key,
        api_version=config.azure_search.api_version,
        index_name=config.azure_search.index_name,
        similarity_threshold=config.azure_search.similarity_threshold,
    )

    passthrough_config = providers.Singleton(
        PassthroughPromptConfig,
        prefix=config.passthrough.prefix,
        suffix=config.passthrough.suffix,
        format_template=config.passthrough.format_template,
        include_question_id=config.passthrough.include_question_id,
        include_metadata=config.passthrough.include_metadata,
    )

    dynamic_prompt_config = providers.Singleton(
        DynamicPromptConfig,
        endpoint=config.dynamic_prompt.endpoint,
        api_key=config.dynamic_prompt.api_key,
        api_version=config.dynamic_prompt.api_version,
        model_name=config.dynamic_prompt.model_name,
        max_tokens=config.dynamic_prompt.max_tokens,
        temperature=config.dynamic_prompt.temperature,
        system_prompt=config.dynamic_prompt.system_prompt,
        prompt_template=config.dynamic_prompt.prompt_template,
    )

    orchestrator_config = providers.Singleton(
        OrchestratorConfig,
        enable_dynamic_prompt=config.orchestrator.enable_dynamic_prompt,
        similarity_threshold=config.orchestrator.similarity_threshold,
        max_parallel_requests=config.orchestrator.max_parallel_requests,
        fallback_to_passthrough=config.orchestrator.fallback_to_passthrough,
        fallback_to_dynamic=config.orchestrator.fallback_to_dynamic,
    )

    # Strategy implementations - transient for fresh instances
    similarity_search_strategy = providers.Factory(
        SimilaritySearchPromptStrategy,
        search_config=azure_search_config,
        telemetry=telemetry,
        max_parallel_requests=config.orchestrator.max_parallel_requests,
    )

    passthrough_strategy = providers.Factory(
        PassthroughPromptStrategy,
        config=passthrough_config,
        telemetry=telemetry,
    )

    dynamic_prompt_strategy = providers.Factory(
        DynamicPromptStrategy,
        config=dynamic_prompt_config,
        telemetry=telemetry,
    )

    # Main orchestrator - transient for fresh instances
    orchestrator = providers.Factory(
        PromptRetrievalOrchestrator,
        config=orchestrator_config,
        telemetry=telemetry,
        similarity_strategy=similarity_search_strategy,
        passthrough_strategy=passthrough_strategy,
        dynamic_strategy=dynamic_prompt_strategy,
    )


def create_container() -> containers.DynamicContainer:
    """
    Create and configure the application container with defaults and environment overrides.
    
    Returns:
        DynamicContainer: Configured container with all services
    """
    container = ApplicationContainer()

    # Configure from environment variables first
    _configure_from_environment(container)

    return container


def _configure_from_environment(container: ApplicationContainer) -> None:
    """Configure container from environment variables with defaults."""
    
    # Environment variable mappings with defaults
    config_mappings = {
        # Telemetry configuration
        ("TELEMETRY_SERVICE_NAME", "telemetry.service_name", "prompt-retrieval"),
        ("TELEMETRY_SERVICE_VERSION", "telemetry.service_version", "0.1.0"),
        
        # Azure Search configuration
        ("AZURE_SEARCH_ENDPOINT", "azure_search.endpoint", "https://demo.search.windows.net"),
        ("AZURE_SEARCH_API_KEY", "azure_search.api_key", "demo-key"),
        ("AZURE_SEARCH_API_VERSION", "azure_search.api_version", "2024-07-01-preview"),
        ("AZURE_SEARCH_INDEX_NAME", "azure_search.index_name", "prompts"),
        ("AZURE_SEARCH_SIMILARITY_THRESHOLD", "azure_search.similarity_threshold", 0.75),
        
        # Passthrough configuration
        ("PASSTHROUGH_PREFIX", "passthrough.prefix", None),
        ("PASSTHROUGH_SUFFIX", "passthrough.suffix", None),
        ("PASSTHROUGH_FORMAT_TEMPLATE", "passthrough.format_template", "Based on your question: {question}"),
        ("PASSTHROUGH_INCLUDE_QUESTION_ID", "passthrough.include_question_id", False),
        ("PASSTHROUGH_INCLUDE_METADATA", "passthrough.include_metadata", True),
        
        # Dynamic prompt configuration
        ("DYNAMIC_PROMPT_ENDPOINT", "dynamic_prompt.endpoint", "https://demo.openai.azure.com"),
        ("DYNAMIC_PROMPT_API_KEY", "dynamic_prompt.api_key", "demo-key"),
        ("DYNAMIC_PROMPT_API_VERSION", "dynamic_prompt.api_version", "2024-02-01"),
        ("DYNAMIC_PROMPT_MODEL_NAME", "dynamic_prompt.model_name", "gpt-4"),
        ("DYNAMIC_PROMPT_TEMPERATURE", "dynamic_prompt.temperature", 0.7),
        ("DYNAMIC_PROMPT_MAX_TOKENS", "dynamic_prompt.max_tokens", 500),
        ("DYNAMIC_PROMPT_SYSTEM_PROMPT", "dynamic_prompt.system_prompt", "You are a helpful assistant that generates prompts based on questions."),
        ("DYNAMIC_PROMPT_PROMPT_TEMPLATE", "dynamic_prompt.prompt_template", None),
        
        # Orchestrator configuration
        ("ORCHESTRATOR_ENABLE_DYNAMIC_PROMPT", "orchestrator.enable_dynamic_prompt", False),
        ("ORCHESTRATOR_SIMILARITY_THRESHOLD", "orchestrator.similarity_threshold", 0.75),
        ("ORCHESTRATOR_MAX_PARALLEL_REQUESTS", "orchestrator.max_parallel_requests", 5),
        ("ORCHESTRATOR_FALLBACK_TO_PASSTHROUGH", "orchestrator.fallback_to_passthrough", True),
        ("ORCHESTRATOR_FALLBACK_TO_DYNAMIC", "orchestrator.fallback_to_dynamic", False),
    }

    # Apply configuration values (environment overrides defaults)
    for env_var, config_path, default_value in config_mappings:
        env_value = os.getenv(env_var)
        
        if env_value is not None:
            # Use environment value, converted to appropriate type
            converted_value = _convert_env_value(env_value, config_path)
            _set_config_value(container.config, config_path, converted_value)
        else:
            # Use default value
            _set_config_value(container.config, config_path, default_value)


def _convert_env_value(value: str, config_path: str) -> any:
    """Convert environment variable string to appropriate type based on config path."""
    
    # Boolean conversions
    if any(key in config_path for key in ["enable_", "include_"]):
        return value.lower() in ("true", "1", "yes", "on")
    
    # Numeric conversions
    if "threshold" in config_path or "temperature" in config_path:
        try:
            return float(value)
        except ValueError:
            return value
    
    if "top_k" in config_path or "max_tokens" in config_path:
        try:
            return int(value)
        except ValueError:
            return value
    
    # String values (including None handling)
    if value.lower() in ("none", "null", ""):
        return None
    
    return value


def _set_config_value(config, path: str, value: any) -> None:
    """Set a nested configuration value using dot notation."""
    parts = path.split(".")
    current = config
    
    # Navigate to the parent of the target
    for part in parts[:-1]:
        current = getattr(current, part)
    
    # Set the final value
    getattr(current, parts[-1]).override(value)
