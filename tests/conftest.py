"""
Shared test configuration and fixtures for the prompt_retrieval package.

This conftest.py provides project-wide fixtures that mock telemetry components
to avoid I/O issues during testing.
"""

import os
from unittest.mock import Mock

import pytest


class MockTelemetryService:
    """Mock TelemetryService that provides the same interface without OpenTelemetry."""

    def __init__(self, *args, **kwargs):
        # Mock logger methods
        self.debug = Mock()
        self.info = Mock()
        self.warning = Mock()
        self.error = Mock()
        self.exception = Mock()
        
        # Mock telemetry methods
        self.record_matched_questions = Mock()
        self.shutdown = Mock()
        
    def start_span(self, name, attributes=None):
        """Mock span context manager."""
        return MockSpan()


class MockSpan:
    """Mock span object."""
    
    def __init__(self):
        self.set_attribute = Mock()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


@pytest.fixture(autouse=True)
def mock_telemetry_globally(monkeypatch):
    """
    Automatically mock TelemetryService across all tests to prevent 
    OpenTelemetry console exporter I/O issues.
    
    This fixture only mocks when we're NOT specifically testing the telemetry module.
    """
    # Only mock if we're not testing the telemetry module itself
    test_name = os.environ.get("PYTEST_CURRENT_TEST", "")
    if "test_telemetry_service.py" not in test_name:
        try:
            import prompt_retrieval.telemetry
            monkeypatch.setattr(
                prompt_retrieval.telemetry, 
                "TelemetryService", 
                MockTelemetryService
            )
        except ImportError:
            # Module not available, skip mocking
            pass


@pytest.fixture(autouse=True) 
def clean_environment():
    """Clean up environment variables that might affect tests."""
    # Store original values
    original_connection_string = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING")
    
    # Clean up for tests
    if "APPLICATIONINSIGHTS_CONNECTION_STRING" in os.environ:
        del os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"]
    
    yield
    
    # Restore original values
    if original_connection_string is not None:
        os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"] = original_connection_string


@pytest.fixture
def mock_telemetry_service():
    """Provide a mock telemetry service for explicit use in tests."""
    return MockTelemetryService()
