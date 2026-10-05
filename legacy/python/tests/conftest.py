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
    # Clipboard routing must not depend on the shell running the tests
    # (herdr panes and SSH sessions switch copies to OSC 52), and OSC 52
    # writes must never reach the developer's real terminal.
    for name in ("HERDR_ENV", "SSH_CONNECTION", "SSH_TTY", "SSH_CLIENT", "PROMPTCRAFT_CLIPBOARD"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr("promptcraft.main._TTY_PATH", str(tmp_path / "no-tty" / "tty"))
    yield
    try:
        os.chdir(orig_cwd)
    except Exception:
        pass
    invalidate_caches()
