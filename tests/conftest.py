"""
Pytest configuration for integration tests.

This file registers custom pytest markers and command-line options.
"""

import pytest


def pytest_addoption(parser):
    """Add custom command-line options"""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests against real Azure resources"
    )


def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test requiring real Azure resources"
    )


def pytest_collection_modifyitems(config, items):
    """Skip integration tests unless --run-integration is specified"""
    if config.getoption("--run-integration"):
        return

    skip_integration = pytest.mark.skip(reason="need --run-integration option to run")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)