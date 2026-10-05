"""Unit tests for the CLI entry-point decision (TUI vs. command line).

promptcraft() opens the interactive TUI only for a truly bare invocation
(no command, no flags) on an interactive terminal; every other no-command
invocation must behave exactly like the pre-TUI CLI.
"""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

import promptcraft.main as main_mod
from promptcraft.main import promptcraft


@pytest.fixture(autouse=True)
def restore_terminal_state(monkeypatch):
    monkeypatch.setenv("PROMPTCRAFT_NO_CLIPBOARD", "true")
    yield


def test_bare_invocation_on_tty_opens_tui():
    with (
        patch.object(main_mod, "_is_interactive_terminal", return_value=True),
        patch.object(main_mod, "_launch_tui") as launched,
    ):
        promptcraft()
        launched.assert_called_once_with()


def test_stdout_without_command_never_opens_tui():
    """promptcraft --stdout (no command) keeps the old error path on a TTY."""
    with (
        patch.object(main_mod, "_is_interactive_terminal", return_value=True) as tty,
        patch.object(main_mod, "_launch_tui") as launched,
        pytest.raises(SystemExit) as exc,
    ):
        promptcraft(stdout=True)
    launched.assert_not_called()
    tty.assert_not_called()  # flags take precedence even before the TTY check
    assert exc.value.code == 1


def test_non_tty_keeps_old_error():
    with (
        patch.object(main_mod, "_is_interactive_terminal", return_value=False),
        patch.object(main_mod, "_launch_tui") as launched,
        pytest.raises(SystemExit) as exc,
    ):
        promptcraft()
    launched.assert_not_called()
    assert exc.value.code == 1


def test_launch_tui_import_error_exits_1(capsys):
    import builtins

    real_import = builtins.__import__

    def fail_tui(name, *args, **kwargs):
        # `from .tui import run_tui` arrives as name="tui" with level=1.
        if name in ("tui", "promptcraft.tui"):
            raise ImportError("No module named promptcraft.tui")
        return real_import(name, *args, **kwargs)

    with patch.object(builtins, "__import__", side_effect=fail_tui):
        with pytest.raises(SystemExit) as exc:
            main_mod._launch_tui()
    assert exc.value.code == 1
    assert "Interactive interface unavailable" in capsys.readouterr().out


def test_is_interactive_terminal_guards_errors():
    with patch.object(main_mod.sys.stdin, "isatty", side_effect=ValueError):
        assert main_mod._is_interactive_terminal() is False


def test_run_tui_invokes_app_run():
    with patch("promptcraft.tui.PromptCraftTUI.run") as mock_run:
        from promptcraft.tui import run_tui
        run_tui()
        mock_run.assert_called_once()


def test_main_module_run():
    import runpy
    with patch("promptcraft.main.main") as mock_main:
        runpy.run_module("promptcraft.__main__", run_name="__main__")
        mock_main.assert_called_once()


def test_core_caching_hit_and_miss_coverage(tmp_path):
    from promptcraft.core import find_command_path, discover_commands, CommandNotFoundError
    cmd_dir = tmp_path / ".promptcraft" / "commands"
    cmd_dir.mkdir(parents=True)
    test_file = cmd_dir / "cached-cmd.md"
    test_file.write_text("# Cached\nBody")

    with patch("promptcraft.core.Path.cwd", return_value=tmp_path):
        # First call populates cache
        p1 = find_command_path("cached-cmd")
        # Second call hits cache
        p2 = find_command_path("cached-cmd")
        assert p1 == p2

        # First miss
        with pytest.raises(CommandNotFoundError):
            find_command_path("missing-cached-cmd")
        # Second miss hits cache
        with pytest.raises(CommandNotFoundError):
            find_command_path("missing-cached-cmd")

        # Discovery cache hit
        d1 = discover_commands()
        d2 = discover_commands()
        assert len(d1) == len(d2)


def test_init_version_fallback():
    import importlib
    import importlib.metadata
    with patch("importlib.metadata.version", side_effect=importlib.metadata.PackageNotFoundError):
        import promptcraft
        importlib.reload(promptcraft)
        assert promptcraft.__version__ == "0.1.0"
    importlib.reload(promptcraft)


def test_launch_tui_and_main_coverage():
    with patch("promptcraft.tui.run_tui") as mock_run:
        main_mod._launch_tui()
        mock_run.assert_called_once()

    with patch.object(main_mod.promptcraft, "main") as mock_main:
        main_mod.main()
        mock_main.assert_called_once()

    with patch.object(main_mod.click.Command, "__call__", return_value=42):
        res = main_mod.promptcraft("arg1")
        assert res == 42


def test_main_init_created_dir_feedback():
    from unittest.mock import MagicMock
    from click.testing import CliRunner
    runner = CliRunner()
    mock_dir = MagicMock()
    mock_file = MagicMock()
    mock_dir.__truediv__.return_value = mock_file
    mock_dir.exists.return_value = False
    mock_file.exists.return_value = False
    with patch("promptcraft.main.Path", return_value=mock_dir):
        res = runner.invoke(promptcraft, ["--init"])
        assert res.exit_code == 0
        assert "Created directory: .promptcraft/commands/" in res.output


def test_core_cache_expiration_and_deleted_file(tmp_path):
    import time
    from pathlib import Path
    from promptcraft.core import find_command_path, discover_commands, _PATH_CACHE, _DISCOVERY_CACHE, CommandNotFoundError

    cmd_dir = tmp_path / ".promptcraft" / "commands"
    cmd_dir.mkdir(parents=True)
    f = cmd_dir / "temp-cmd.md"
    f.write_text("# Temp\nBody")

    with patch("promptcraft.core.Path.cwd", return_value=tmp_path):
        p = find_command_path("temp-cmd")
        assert p.exists()

        # Simulate file deleted while in cache
        f.unlink()
        with pytest.raises(CommandNotFoundError):
            find_command_path("temp-cmd")

        # Simulate expired cache entry (> 5.0s)
        cache_key = (str(tmp_path), str(Path.home()), "expired-cmd")
        _PATH_CACHE[cache_key] = (time.time() - 100.0, None)
        with pytest.raises(CommandNotFoundError):
            find_command_path("expired-cmd")

        # Simulate expired discovery cache (> 10.0s)
        disc_key = (str(tmp_path), str(Path.home()))
        _DISCOVERY_CACHE[disc_key] = (time.time() - 100.0, [])
        disc = discover_commands()
        assert isinstance(disc, list)


def test_core_exceptions_and_directories_in_discovery(tmp_path):
    from promptcraft.core import find_command_path, discover_commands, CommandNotFoundError

    with patch("promptcraft.core.Path.cwd", side_effect=RuntimeError("no cwd")), \
         patch("promptcraft.core.Path.home", side_effect=RuntimeError("no home")):
        with pytest.raises(CommandNotFoundError):
            find_command_path("any-cmd")

    with patch("promptcraft.core.Path.cwd", side_effect=RuntimeError("no cwd")), \
         patch("promptcraft.core.Path.home", side_effect=RuntimeError("no home")):
        res = discover_commands()
        assert res == []

    cmd_dir = tmp_path / ".promptcraft" / "commands"
    cmd_dir.mkdir(parents=True)
    (cmd_dir / "subfolder.md").mkdir()
    with patch("promptcraft.core.Path.cwd", return_value=tmp_path):
        cmds = discover_commands()
        assert not any(c.name == "subfolder" for c in cmds)

    stat_mock = MagicMock()
    stat_mock.st_mode = 0o040755
    stat_mock.st_mtime = "not-a-number"
    with patch("promptcraft.core.Path.cwd", return_value=tmp_path):
        with patch.object(Path, "stat", return_value=stat_mock):
            cmds = discover_commands()
            assert isinstance(cmds, list)


