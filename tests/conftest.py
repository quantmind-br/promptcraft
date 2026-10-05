"""Test configuration and fixtures for PromptCraft test suite."""

import os
from pathlib import Path
import pytest
from promptcraft.core import invalidate_caches


@pytest.fixture(autouse=True)
def test_environment_isolation(tmp_path, monkeypatch):
    """Isolate HOME, restore working directory, and clear caches between tests."""
    orig_cwd = os.getcwd()
    invalidate_caches()
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(fake_home))
    yield
    try:
        os.chdir(orig_cwd)
    except Exception:
        pass
    invalidate_caches()
