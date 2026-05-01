"""Shared fixtures for HTTP integration tests."""

from __future__ import annotations

import pytest

from agent.http.app import create_app


@pytest.fixture
def app():
    application = create_app()
    yield application
    application.dependency_overrides.clear()
