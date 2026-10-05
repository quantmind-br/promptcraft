"""OSC 52 clipboard routing for herdr panes and SSH sessions."""

import base64
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from promptcraft import main
from promptcraft.main import (
    CLIPBOARD_NATIVE,
    CLIPBOARD_OSC52,
    OSC52_MAX_BYTES,
    _copy_to_clipboard,
    _copy_to_clipboard_route,
    _should_prefer_osc52,
    promptcraft,
)


@pytest.fixture(autouse=True)
def clipboard_enabled(monkeypatch):
    """CI runners set CI=true, which disables every clipboard route."""
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("PROMPTCRAFT_NO_CLIPBOARD", raising=False)


@pytest.fixture
def tty(tmp_path, monkeypatch):
    """Redirect OSC 52 writes to a file standing in for the controlling terminal."""
    path = tmp_path / "tty"
    path.touch()
    monkeypatch.setattr(main, "_TTY_PATH", str(path))
    return path


def osc52(text):
    return "\x1b]52;c;" + base64.b64encode(text.encode("utf-8")).decode("ascii") + "\x07"


class TestShouldPreferOsc52:
    def test_local_session_uses_native_clipboard(self):
        assert _should_prefer_osc52() is False

    def test_herdr_pane(self, monkeypatch):
        monkeypatch.setenv("HERDR_ENV", "1")
        assert _should_prefer_osc52() is True

    @pytest.mark.parametrize("name", ["SSH_CONNECTION", "SSH_TTY", "SSH_CLIENT"])
    def test_ssh_session(self, monkeypatch, name):
        monkeypatch.setenv(name, "203.0.113.5 50000 22")
        assert _should_prefer_osc52() is True

    def test_override_forces_osc52(self, monkeypatch):
        monkeypatch.setenv("PROMPTCRAFT_CLIPBOARD", "OSC52")
        assert _should_prefer_osc52() is True

    def test_override_forces_native_inside_herdr(self, monkeypatch):
        monkeypatch.setenv("HERDR_ENV", "1")
        monkeypatch.setenv("PROMPTCRAFT_CLIPBOARD", "native")
        assert _should_prefer_osc52() is False

    def test_unknown_override_keeps_detection(self, monkeypatch):
        monkeypatch.setenv("HERDR_ENV", "1")
        monkeypatch.setenv("PROMPTCRAFT_CLIPBOARD", "auto")
        assert _should_prefer_osc52() is True


class TestCopyRoute:
    def test_herdr_pane_with_desktop_display_writes_osc52(self, monkeypatch, tty):
        # A herdr server started on the desktop leaks WAYLAND_DISPLAY into
        # panes; the native clipboard would be the desktop's, not the viewer's.
        monkeypatch.setenv("HERDR_ENV", "1")
        monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-1")
        monkeypatch.setenv("DISPLAY", ":0")
        with patch("promptcraft.main.pyperclip.copy") as native_copy:
            assert _copy_to_clipboard_route("café 🚀") == CLIPBOARD_OSC52
        native_copy.assert_not_called()
        assert tty.read_text(encoding="ascii") == osc52("café 🚀")

    def test_ssh_without_display_writes_osc52(self, monkeypatch, tty):
        monkeypatch.setenv("SSH_CLIENT", "203.0.113.5 50000 22")
        monkeypatch.delenv("DISPLAY", raising=False)
        assert _copy_to_clipboard("hello", "cmd") is True
        assert tty.read_text(encoding="ascii") == osc52("hello")

    def test_headless_local_session_falls_back_to_osc52(self, tty):
        with patch("promptcraft.main._is_headless_environment", return_value=True):
            assert _copy_to_clipboard_route("hello") == CLIPBOARD_OSC52
        assert tty.read_text(encoding="ascii") == osc52("hello")

    def test_native_copy_leaves_terminal_untouched(self, tty):
        with patch("promptcraft.main._is_headless_environment", return_value=False), \
             patch("promptcraft.main.pyperclip.copy") as native_copy:
            assert _copy_to_clipboard_route("hello") == CLIPBOARD_NATIVE
        native_copy.assert_called_once_with("hello")
        assert tty.read_text(encoding="ascii") == ""

    def test_native_failure_falls_back_to_osc52(self, tty):
        with patch("promptcraft.main._is_headless_environment", return_value=False), \
             patch("promptcraft.main.pyperclip.copy", side_effect=Exception("no wl-copy")):
            assert _copy_to_clipboard_route("hello") == CLIPBOARD_OSC52
        assert tty.read_text(encoding="ascii") == osc52("hello")

    @pytest.mark.parametrize("name", ["PROMPTCRAFT_NO_CLIPBOARD", "CI"])
    def test_disabled_clipboard_skips_osc52(self, monkeypatch, tty, name):
        monkeypatch.setenv("HERDR_ENV", "1")
        monkeypatch.setenv(name, "true")
        assert _copy_to_clipboard_route("hello") is None
        assert tty.read_text(encoding="ascii") == ""

    def test_missing_terminal_reports_failure(self, monkeypatch):
        # conftest points _TTY_PATH at a path that cannot be opened
        monkeypatch.setenv("HERDR_ENV", "1")
        assert _copy_to_clipboard_route("hello") is None

    @pytest.mark.parametrize("text", ["", "x" * (OSC52_MAX_BYTES + 1)])
    def test_empty_or_oversized_text_is_not_sent(self, monkeypatch, tty, text):
        monkeypatch.setenv("HERDR_ENV", "1")
        assert _copy_to_clipboard_route(text) is None
        assert tty.read_text(encoding="ascii") == ""

    def test_text_at_size_limit_is_sent(self, monkeypatch, tty):
        monkeypatch.setenv("HERDR_ENV", "1")
        assert _copy_to_clipboard_route("x" * OSC52_MAX_BYTES) == CLIPBOARD_OSC52

    def test_custom_writer_replaces_terminal_write(self, monkeypatch, tty):
        monkeypatch.setenv("HERDR_ENV", "1")
        written = []
        assert _copy_to_clipboard_route("hello", written.append) == CLIPBOARD_OSC52
        assert written == ["hello"]
        assert tty.read_text(encoding="ascii") == ""

    def test_failing_writer_reports_failure(self, monkeypatch):
        monkeypatch.setenv("HERDR_ENV", "1")

        def broken_writer(text):
            raise RuntimeError("driver gone")

        assert _copy_to_clipboard_route("hello", broken_writer) is None


class TestCliMessages:
    @patch("promptcraft.main.process_command", return_value="Generated prompt")
    def test_osc52_copy_is_reported_as_sent(self, _process, monkeypatch, tty):
        monkeypatch.setenv("HERDR_ENV", "1")
        result = CliRunner().invoke(promptcraft, ["/demo"])
        assert result.exit_code == 0
        assert "sent to clipboard via terminal (OSC 52)" in result.output
        assert "Generated prompt" not in result.output
        assert tty.read_text(encoding="ascii") == osc52("Generated prompt")

    @patch("promptcraft.main.process_command", return_value="Generated prompt")
    def test_osc52_failure_prints_prompt(self, _process, monkeypatch):
        monkeypatch.setenv("HERDR_ENV", "1")
        result = CliRunner().invoke(promptcraft, ["/demo"])
        assert result.exit_code == 0
        assert "Clipboard unavailable" in result.output
        assert "Generated prompt" in result.output
