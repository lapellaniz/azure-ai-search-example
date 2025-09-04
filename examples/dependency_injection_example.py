#!/usr/bin/env python3
"""
Example demonstrating dependency injection with dependency-injector.

This example shows how to use the dependency injection container to resolve
services and configurations for the prompt retrieval framework.

Run with: poetry run python examples/dependency_injection_example.py
"""

import asyncio
import os
from typing import List

from dependency_injector.wiring import Provide, inject

from prompt_retrieval import (
    get_orchestrator,
    create_container,
    ApplicationContainer,
    PromptRetrievalOrchestrator,
)
from prompt_retrieval.common.models import QuestionInput


async def example_simple_usage():
    """Example using the convenience function."""
    print("🔧 Example 1: Simple Usage with Convenience Function")
    print("-" * 50)
    
    # Set environment variables for configuration
    os.environ.update({
        "AZURE_SEARCH_ENDPOINT": "https://example.search.windows.net",
        "AZURE_SEARCH_API_KEY": "demo-key-12345",
        "AZURE_SEARCH_INDEX_NAME": "prompts-index",
        "TELEMETRY_SERVICE_NAME": "di-example",
        "TELEMETRY_SERVICE_VERSION": "1.0.0",
    })
    
    try:
        # Get orchestrator using convenience function
        orchestrator = get_orchestrator()
        print(f"✅ Orchestrator created: {type(orchestrator).__name__}")
        
        # Try to retrieve prompts (will fail with demo credentials but shows DI working)
        try:
            result = await orchestrator.retrieve_prompts("health-assessment-demo")
            print(f"📊 Retrieved {len(result.results)} results")
            
        except Exception as e:
            print(f"⚠️  Expected error (demo credentials): {type(e).__name__}")
            print("   This demonstrates the DI system is working correctly!")
            
    except ValueError as e:
        print(f"❌ Configuration error: {e}")


async def example_direct_container():
    """Example using direct container resolution."""
    print("\n📦 Example 2: Direct Container Usage")
    print("-" * 40)
    
    # Create container with custom configuration
    container = create_container()
    
    # Override some configuration values
    container.config.azure_search.similarity_threshold.override(0.9)
    container.config.orchestrator.enable_parallel.override(False)
    
    # Resolve services
    orchestrator = container.orchestrator()
    azure_config = container.azure_search_config()
    telemetry = container.telemetry()
    
    print(f"✅ Services resolved:")
    print(f"   - Orchestrator: {type(orchestrator).__name__}")
    print(f"   - Azure config similarity threshold: {azure_config.similarity_threshold}")
    print(f"   - Telemetry service: {type(telemetry).__name__}")


def example_testing_with_overrides():
    """Example showing how to override services for testing."""
    print("\n🧪 Example 3: Testing with Container Overrides")
    print("-" * 45)
    
    from unittest.mock import MagicMock
    from prompt_retrieval.common.telemetry import TelemetryService
    
    container = create_container()
    
    # Create mock telemetry service
    mock_telemetry = MagicMock(spec=TelemetryService)
    mock_telemetry.service_name = "mock-service"
    mock_telemetry.service_version = "mock-version"
    
    # Override the telemetry provider
    container.telemetry.override(mock_telemetry)
    
    # Resolve services - orchestrator will get the mock telemetry
    orchestrator = container.orchestrator()
    telemetry = container.telemetry()
    
    print(f"✅ Mock telemetry injected:")
    print(f"   - Service name: {telemetry.service_name}")
    print(f"   - Service version: {telemetry.service_version}")
    print(f"   - Mock object type: {type(telemetry).__name__}")
    
    # Reset override
    container.telemetry.reset_override()
    print("   - Override reset successfully")


# Example using dependency injection decorators
@inject
async def example_with_injection(
    orchestrator: PromptRetrievalOrchestrator = Provide[ApplicationContainer.orchestrator]
):
    """Example using dependency injection decorators."""
    print("\n🎯 Example 4: Dependency Injection with Decorators")
    print("-" * 50)
    
    print(f"✅ Orchestrator injected: {type(orchestrator).__name__}")
    print("   Dependencies are automatically resolved and injected!")


def example_configuration_from_environment():
    """Example showing configuration from environment variables."""
    print("\n⚙️  Example 5: Configuration from Environment")
    print("-" * 45)
    
    # Set various environment variables
    env_vars = {
        "AZURE_SEARCH_SIMILARITY_THRESHOLD": "0.85",
        "ORCHESTRATOR_ENABLE_PARALLEL": "false",
        "TELEMETRY_SERVICE_NAME": "env-configured-service",
        "PASSTHROUGH_FORMAT_TEMPLATE": "Environment template: {question}",
    }
    
    # Apply environment variables
    for key, value in env_vars.items():
        os.environ[key] = value
    
    # Create container - it will pick up environment variables
    container = create_container()
    
    # Check that environment variables were applied
    azure_config = container.azure_search_config()
    orchestrator_config = container.orchestrator_config()
    telemetry = container.telemetry()
    passthrough_config = container.passthrough_config()
    
    print(f"✅ Configuration from environment:")
    print(f"   - Azure similarity threshold: {azure_config.similarity_threshold}")
    print(f"   - Max parallel requests: {orchestrator_config.max_parallel_requests}")
    print(f"   - Enable dynamic prompt: {orchestrator_config.enable_dynamic_prompt}")
    print(f"   - Passthrough template: {passthrough_config.format_template}")


async def main():
    """Main example function."""
    print("🔧 Dependency Injection with dependency-injector")
    print("=" * 50)
    
    # Set up basic environment
    os.environ.update({
        "AZURE_SEARCH_ENDPOINT": "https://example.search.windows.net",
        "AZURE_SEARCH_API_KEY": "demo-key-12345",
        "AZURE_SEARCH_INDEX_NAME": "prompts-index",
    })
    
    # Run examples
    await example_simple_usage()
    await example_direct_container()
    example_testing_with_overrides()
    
    # For injection example, we need to wire the container
    container = create_container()
    container.wire(modules=[__name__])
    
    try:
        await example_with_injection()
    finally:
        container.unwire()
    
    example_configuration_from_environment()
    
    print("\n🎉 All examples completed!")
    print("\nKey Benefits:")
    print("✅ Transient strategies and orchestrator for fresh instances")
    print("✅ Singleton configs and telemetry for efficiency")
    print("✅ Environment variable configuration with defaults")
    print("✅ Easy testing with service overrides")
    print("✅ Decorator-based dependency injection")


if __name__ == "__main__":
    asyncio.run(main())
