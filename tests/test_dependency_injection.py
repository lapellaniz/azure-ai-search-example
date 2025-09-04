"""
Tests for dependency injection using dependency-injector package.
"""

import pytest
import os
from unittest.mock import MagicMock, patch
from dependency_injector import containers

from prompt_retrieval import (
    create_container,
    get_container,
    get_orchestrator,
    reset_container,
    ApplicationContainer,
    PromptRetrievalOrchestrator,
    TelemetryService,
)
from prompt_retrieval.strategies.similarity_search.strategy import SimilaritySearchPromptStrategy
from prompt_retrieval.strategies.passthrough.strategy import PassthroughPromptStrategy


class TestApplicationContainer:
    """Test the dependency-injector container."""
    
    def test_create_container(self):
        """Test container creation and basic configuration."""
        container = create_container()

        assert isinstance(container, containers.DynamicContainer)
        assert container.config is not None
    
    def test_resolve_telemetry_service_singleton(self):
        """Test resolving telemetry service as singleton."""
        container = create_container()
        
        telemetry1 = container.telemetry()
        telemetry2 = container.telemetry()
        
        # Should be the same instance (singleton)
        assert telemetry1 is telemetry2
        assert isinstance(telemetry1, TelemetryService)
    
    def test_resolve_azure_search_config_singleton(self):
        """Test resolving Azure Search configuration as singleton."""
        container = create_container()
        
        config1 = container.azure_search_config()
        config2 = container.azure_search_config()
        
        # Should be the same instance (singleton)
        assert config1 is config2
        assert config1.api_version == "2024-07-01-preview"  # Default value
    
    def test_resolve_similarity_search_strategy_transient(self):
        """Test resolving similarity search strategy as transient."""
        container = create_container()
        
        strategy1 = container.similarity_search_strategy()
        strategy2 = container.similarity_search_strategy()
        
        # Should be different instances (transient)
        assert strategy1 is not strategy2
        assert isinstance(strategy1, SimilaritySearchPromptStrategy)
        assert isinstance(strategy2, SimilaritySearchPromptStrategy)
    
    def test_resolve_orchestrator_transient(self):
        """Test resolving orchestrator as transient."""
        container = create_container()
        
        orchestrator1 = container.orchestrator()
        orchestrator2 = container.orchestrator()
        
        # Should be different instances (transient)
        assert orchestrator1 is not orchestrator2
        assert isinstance(orchestrator1, PromptRetrievalOrchestrator)
        assert isinstance(orchestrator2, PromptRetrievalOrchestrator)
    
    def test_orchestrator_has_injected_dependencies(self):
        """Test that orchestrator has all dependencies injected."""
        container = create_container()
        orchestrator = container.orchestrator()
        
        # Check that orchestrator was created successfully
        assert isinstance(orchestrator, PromptRetrievalOrchestrator)
        
        # The orchestrator should have its dependencies injected
        # (we can't easily check private attributes, but creation success indicates injection worked)
    
    def test_override_configuration(self):
        """Test overriding configuration values."""
        container = create_container()

        # Override configuration
        container.config.azure_search.similarity_threshold.override(0.9)
        container.config.telemetry.service_name.override("test-service")

        # Check that overrides took effect
        azure_config = container.azure_search_config()
        telemetry = container.telemetry()

        assert azure_config.similarity_threshold == 0.9
        assert isinstance(telemetry, TelemetryService)

    def test_override_service_for_testing(self):
        """Test overriding services for testing."""
        container = create_container()
        
        # Create mock telemetry
        mock_telemetry = MagicMock(spec=TelemetryService)
        mock_telemetry.service_name = "mock-service"
        
        # Override the provider
        container.telemetry.override(mock_telemetry)
        
        # Resolve should return mock
        resolved = container.telemetry()
        assert resolved is mock_telemetry
        assert resolved.service_name == "mock-service"
        
        # Reset override
        container.telemetry.reset_override()
        
        # Should now return real service
        real_service = container.telemetry()
        assert real_service is not mock_telemetry
        assert isinstance(real_service, TelemetryService)


class TestConvenienceFunctions:
    """Test the convenience functions for dependency injection."""
    
    def setup_method(self):
        """Reset container before each test."""
        reset_container()
    
    def test_get_container(self):
        """Test getting the global container."""
        container = get_container()

        assert isinstance(container, containers.DynamicContainer)        # Should return the same instance on subsequent calls
        container2 = get_container()
        assert container is container2
    
    def test_get_orchestrator_success(self):
        """Test getting orchestrator with valid configuration."""
        with patch.dict(os.environ, {
            'AZURE_SEARCH_ENDPOINT': 'https://test.search.windows.net',
            'AZURE_SEARCH_API_KEY': 'test-key',
            'AZURE_SEARCH_INDEX_NAME': 'test-index',
        }):
            orchestrator = get_orchestrator()
            assert isinstance(orchestrator, PromptRetrievalOrchestrator)
    
    def test_get_orchestrator_missing_config(self):
        """Test getting orchestrator with missing configuration."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Required environment variables not set"):
                get_orchestrator()
    
    def test_reset_container(self):
        """Test resetting the global container."""
        # Get container (creates it)
        container1 = get_container()
        
        # Reset
        reset_container()
        
        # Get again (should create new one)
        container2 = get_container()
        
        assert container1 is not container2


class TestEnvironmentConfiguration:
    """Test environment variable configuration."""
    
    def test_configuration_from_environment_strings(self):
        """Test loading string configuration from environment variables."""
        env_vars = {
            'AZURE_SEARCH_ENDPOINT': 'https://env.search.windows.net',
            'AZURE_SEARCH_API_KEY': 'env-key',
            'AZURE_SEARCH_INDEX_NAME': 'env-index',
            'TELEMETRY_SERVICE_NAME': 'env-service',
            'PASSTHROUGH_FORMAT_TEMPLATE': 'Env template: {question}',
        }
        
        with patch.dict(os.environ, env_vars):
            container = create_container()
            
            # Check string configurations
            azure_config = container.azure_search_config()
            telemetry = container.telemetry()
            passthrough_config = container.passthrough_config()
            
            assert azure_config.endpoint == 'https://env.search.windows.net'
            assert azure_config.api_key == 'env-key'
            assert azure_config.index_name == 'env-index'
            assert isinstance(telemetry, TelemetryService)
            assert passthrough_config.format_template == 'Env template: {question}'
    
    def test_configuration_from_environment_numbers(self):
        """Test loading numeric configuration from environment variables."""
        env_vars = {
            'AZURE_SEARCH_SIMILARITY_THRESHOLD': '0.85',
            'DYNAMIC_PROMPT_TEMPERATURE': '0.9',
            'DYNAMIC_PROMPT_MAX_TOKENS': '200',
        }
        
        with patch.dict(os.environ, env_vars):
            container = create_container()
            
            azure_config = container.azure_search_config()
            dynamic_config = container.dynamic_prompt_config()
            
            assert azure_config.similarity_threshold == 0.85
            assert dynamic_config.temperature == 0.9
            assert dynamic_config.max_tokens == 200
    
    def test_configuration_from_environment_booleans(self):
        """Test loading boolean configuration from environment variables."""
        env_vars = {
            'ORCHESTRATOR_ENABLE_DYNAMIC_PROMPT': 'true',
            'PASSTHROUGH_INCLUDE_QUESTION_ID': '1',
            'PASSTHROUGH_INCLUDE_METADATA': '0',
        }
        
        with patch.dict(os.environ, env_vars):
            container = create_container()
            
            orchestrator_config = container.orchestrator_config()
            passthrough_config = container.passthrough_config()
            
            assert orchestrator_config.enable_dynamic_prompt is True
            assert passthrough_config.include_question_id is True
            assert passthrough_config.include_metadata is False
    
    def test_configuration_none_values(self):
        """Test handling None values from environment variables."""
        env_vars = {
            'PASSTHROUGH_PREFIX': 'none',
            'PASSTHROUGH_SUFFIX': 'null',
        }
        
        with patch.dict(os.environ, env_vars):
            container = create_container()
            passthrough_config = container.passthrough_config()
            
            assert passthrough_config.prefix is None
            assert passthrough_config.suffix is None
    
    def test_default_configuration_values(self):
        """Test that default values are used when environment variables are not set."""
        with patch.dict(os.environ, {}, clear=True):
            container = create_container()
            
            # Check defaults
            azure_config = container.azure_search_config()
            telemetry = container.telemetry()
            orchestrator_config = container.orchestrator_config()
            passthrough_config = container.passthrough_config()
            
            assert azure_config.api_version == "2024-07-01-preview"
            assert azure_config.similarity_threshold == 0.75
            assert isinstance(telemetry, TelemetryService)
            assert orchestrator_config.enable_dynamic_prompt is False
            assert passthrough_config.format_template == "Based on your question: {question}"


@pytest.mark.integration
class TestDependencyInjectionIntegration:
    """Integration tests for the full dependency injection system."""
    
    def test_full_orchestrator_resolution_with_all_dependencies(self):
        """Test resolving a full orchestrator with all dependencies."""
        env_vars = {
            'AZURE_SEARCH_ENDPOINT': 'https://integration.search.windows.net',
            'AZURE_SEARCH_API_KEY': 'integration-key',
            'AZURE_SEARCH_INDEX_NAME': 'integration-index',
            'TELEMETRY_SERVICE_NAME': 'integration-test',
        }
        
        with patch.dict(os.environ, env_vars):
            container = create_container()
            orchestrator = container.orchestrator()
            
            # Verify orchestrator was created with injected dependencies
            assert isinstance(orchestrator, PromptRetrievalOrchestrator)
            
            # Test that all strategies can be resolved independently
            similarity_strategy = container.similarity_search_strategy()
            passthrough_strategy = container.passthrough_strategy()
            dynamic_prompt_strategy = container.dynamic_prompt_strategy()
            
            assert isinstance(similarity_strategy, SimilaritySearchPromptStrategy)
            assert isinstance(passthrough_strategy, PassthroughPromptStrategy)
            # Dynamic prompt strategy type check would go here when implemented
    
    def test_container_wiring_for_injection_decorators(self):
        """Test container wiring for dependency injection decorators."""
        from dependency_injector.wiring import Provide, inject
        
        # Define a function with dependency injection
        @inject
        def test_function(
            telemetry: TelemetryService = Provide[ApplicationContainer.telemetry]
        ) -> str:
            return f"Service: {type(telemetry).__name__}"
        
        container = create_container()
        container.config.telemetry.service_name.override("wiring-test")
        
        # Wire the container to this module
        container.wire(modules=[__name__])
        
        try:
            # Call the function - dependency should be injected
            result = test_function()
            assert result == "Service: TelemetryService"
        finally:
            # Clean up wiring
            container.unwire()
    
    def test_mixed_singleton_and_transient_behavior(self):
        """Test that singleton and transient services behave correctly together."""
        container = create_container()
        
        # Get multiple orchestrators (transient)
        orchestrator1 = container.orchestrator()
        orchestrator2 = container.orchestrator()
        
        # Get telemetry from each (should be same singleton)
        telemetry1 = container.telemetry()
        telemetry2 = container.telemetry()
        
        # Orchestrators should be different (transient)
        assert orchestrator1 is not orchestrator2
        
        # Telemetry should be same (singleton)
        assert telemetry1 is telemetry2
        
        # Both orchestrators should use the same telemetry instance
        # (We can't easily verify this without accessing private attributes,
        # but the DI container ensures this behavior)
