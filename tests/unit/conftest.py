"""Pytest configuration for unit tests.

This file sets up mocks for google.adk and other heavy dependencies
BEFORE any test modules are imported, allowing isolated unit testing.
"""
import sys
from unittest.mock import MagicMock


def pytest_configure(config):
    """Called before test collection. Set up mocks for external dependencies."""
    # Mock google.* modules to avoid import errors
    mock_modules = [
        "google",
        "google.genai",
        "google.genai.types",
        "google.adk",
        "google.adk.agents",
        "google.adk.apps",
        "google.adk.apps.app",
        "google.adk.models",
        "google.adk.agents.context_cache_config",
        "google.adk.apps.events_compaction_config",
        # OpenTelemetry
        "opentelemetry",
        "opentelemetry.instrumentation",
        "opentelemetry.instrumentation.google_genai",
        # Vertex AI for embedding service
        "vertexai",
        "vertexai.language_models",
    ]
    
    for mod in mock_modules:
        if mod not in sys.modules:
            sys.modules[mod] = MagicMock()
