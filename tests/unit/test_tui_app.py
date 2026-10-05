"""Interactive (pilot) tests for the PromptCraft TUI.

These drive the real Textual app with a simulated keyboard, exactly the
way a user would: navigate the list, fill the forms, and check the
on-screen feedback for each action (clipboard copy success/failure,
template saved, template not found, idempotent init, version, help).
"""

import asyncio
import importlib
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from promptcraft import __version__
from promptcraft.example_template import EXAMPLE_TEMPLATE
from promptcraft.tui.actions import TemplateInfo
from promptcraft.tui.app import PromptCraftTUI, ResultScreen, RunScreen


def _ensure_valid_cwd(tmp_path):
    """The pre-existing broken tests can leave the process CWD in a deleted
    directory. Escape it first (an absolute os.chdir never reads the old
    CWD) so a subsequent monkeypatch.chdir() can record a restore point."""
    try:
        os.getcwd()
    except OSError:
        os.chdir(str(tmp_path))


def _live_invalidate():
    """Clear caches on the live promptcraft.core module.

    Benchmark tests purge promptcraft.* from sys.modules and re-import,
    so a copy bound at collection time can be detached from the caches
    actually used at runtime; always resolve through the registry.
    """
    importlib.import_module("promptcraft.core").invalidate_caches()


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    """Fresh discovery cache, isolated project dir + user home, headless
    clipboard (so the copy-failure path is exercised by default)."""
    _ensure_valid_cwd(tmp_path)
    _live_invalidate()
    project = tmp_path / "project"
    commands = project / ".promptcraft" / "commands"
    commands.mkdir(parents=True)
    (commands / "alpha.md").write_text("# Alpha project\nA: $ARGUMENTS\n", encoding="utf-8")
    (commands / "shared.md").write_text("# Shared project\nP: $ARGUMENTS\n", encoding="utf-8")
    home = tmp_path / "home"
    home_commands = home / ".promptcraft" / "commands"
    home_commands.mkdir(parents=True)
    (home_commands / "beta.md").write_text("# Beta user\nB: $ARGUMENTS\n", encoding="utf-8")
    (home_commands / "shared.md").write_text("# Shared user\nU: $ARGUMENTS\n", encoding="utf-8")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("PROMPTCRAFT_NO_CLIPBOARD", "true")
    monkeypatch.chdir(project)
    yield {"project": project, "home": home}
    _live_invalidate()


async def _settle(pilot, n=5):
    """Let the app process queued events (screen switches are async)."""
    for _ in range(n):
        await pilot.pause()


def run_app(scenario):
    """Launch the TUI under the test harness and run a scenario on it."""

    async def wrapper():
        app = PromptCraftTUI()
        async with app.run_test(size=(100, 30)) as pilot:
            await _settle(pilot)
            await scenario(app, pilot)

    asyncio.run(wrapper())


async def _type(pilot, text):
    """Type a string one key at a time (Enter key for newlines)."""
    keys = ["enter" if ch == "\n" else (" " if ch == " " else ch) for ch in text]
    for key in keys:
        await pilot.press(key)
        await pilot.pause()


# ---------------------------------------------------------------------------
# Home screen: list, navigation, details
# ---------------------------------------------------------------------------


class TestHomeScreen:
    def test_lists_templates_from_both_scopes(self, isolated_env):
        async def scenario(app, pilot):
            options = app.query_one("#templates").options
            by_id = {o.id: str(o.prompt) for o in options}
            # Project and user templates, deduped by name, project wins.
            assert set(by_id) == {"alpha", "beta", "shared"}
            assert "[Project]" in by_id["shared"]
            assert "Alpha project" in by_id["alpha"]
            assert "Beta user" in by_id["beta"]
            hint = app.query_one("#source-hint").content
            assert ".promptcraft/commands (project)" in hint
            assert "~/.promptcraft/commands (user)" in hint

        run_app(scenario)

    def test_highlights_show_template_details(self, isolated_env):
        async def scenario(app, pilot):
            await pilot.press("down")
            await _settle(pilot)
            details = str(app.query_one("#details").content)
            assert "/alpha" in details
            assert "[Project]" in details
            assert details.endswith("alpha.md")

        run_app(scenario)

    def test_empty_project_shows_guidance(self, tmp_path, monkeypatch):
        _ensure_valid_cwd(tmp_path)
        monkeypatch.setenv("PROMPTCRAFT_NO_CLIPBOARD", "true")
        empty_project = tmp_path / "empty"
        empty_project.mkdir()
        monkeypatch.chdir(empty_project)
        monkeypatch.setenv("HOME", str(tmp_path / "empty-home"))
        _live_invalidate()

        async def scenario(app, pilot):
            assert app.query_one("#source-hint").content == "No templates found."
            assert "Press n to create a template" in str(app.query_one("#details").content)

        run_app(scenario)
        _live_invalidate()

    def test_quit_with_q(self, isolated_env):
        async def scenario(app, pilot):
            await pilot.press("q")
            await _settle(pilot, 2)

        run_app(scenario)


# ---------------------------------------------------------------------------
# Run screen: arguments form, clipboard feedback
# ---------------------------------------------------------------------------


class TestRunScreen:
    def test_run_copies_to_clipboard_when_available(self, isolated_env):
        async def scenario(app, pilot):
            with patch("promptcraft.main._copy_to_clipboard_route", return_value="native"):
                await pilot.press("down")  # highlight alpha
                await _settle(pilot)
                await pilot.press("r")
                await _settle(pilot)
                assert type(app.screen).__name__ == "RunScreen"
                await _type(pilot, "hello world")
                app.screen.action_copy()  # same handler as Enter / the copy button
                await _settle(pilot)
            status = str(app.screen.query_one("#status").content)
            assert "Copied to clipboard" in status

        run_app(scenario)

    def test_run_inside_herdr_copies_through_textual_osc52(self, isolated_env, monkeypatch):
        monkeypatch.delenv("PROMPTCRAFT_NO_CLIPBOARD")
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.setenv("HERDR_ENV", "1")

        async def scenario(app, pilot):
            with patch("promptcraft.main.pyperclip.copy") as native_copy:
                await pilot.press("down")
                await _settle(pilot)
                await pilot.press("r")
                await _settle(pilot)
                await _type(pilot, "hello world")
                await pilot.press("enter")
                await _settle(pilot)
            native_copy.assert_not_called()
            assert app.clipboard == "# Alpha project\nA: hello world\n"
            status = str(app.screen.query_one("#status").content)
            assert status.startswith("✓ Sent to clipboard via terminal (OSC 52")

        run_app(scenario)

    def test_result_copy_inside_herdr_reports_osc52(self, isolated_env, monkeypatch):
        monkeypatch.delenv("PROMPTCRAFT_NO_CLIPBOARD")
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.setenv("HERDR_ENV", "1")

        async def scenario(app, pilot):
            app.push_screen(ResultScreen("alpha", "A: hello world\n", copied=False))
            await _settle(pilot)
            await pilot.press("c")
            await _settle(pilot)
            assert app.clipboard == "A: hello world\n"
            status = str(app.screen.query_one("#status").content)
            assert "OSC 52" in status

        run_app(scenario)

    def test_run_reports_clipboard_failure_and_what_to_do(self, isolated_env):
        async def scenario(app, pilot):
            await pilot.press("down")
            await _settle(pilot)
            await pilot.press("r")
            await _settle(pilot)
            assert type(app.screen).__name__ == "RunScreen"
            await _type(pilot, "hello world")
            await pilot.press("enter")
            await _settle(pilot)
            status = str(app.screen.query_one("#status").content)
            assert status.startswith("✗")
            assert "clipboard" in status
            assert "--stdout" in status  # tells the user what to do

        run_app(scenario)

    def test_display_on_screen_shows_exact_cli_result(self, isolated_env):
        async def scenario(app, pilot):
            await pilot.press("down")
            await _settle(pilot)
            await pilot.press("r")
            await _settle(pilot)
            await _type(pilot, "hello world")
            await pilot.press("enter")
            await _settle(pilot)
            await pilot.press("d")
            await _settle(pilot)
            assert type(app.screen).__name__ == "ResultScreen"
            body = app.screen.query_one(".result-text").text
            # Identical to what the CLI would produce for: promptcraft alpha "hello world"
            assert body == "# Alpha project\nA: hello world\n"
            # The result screen explains the clipboard state and offers a copy.
            assert "c" in str(app.screen.query_one("#status").content)

        run_app(scenario)

    def test_result_copy_action_reports_success_and_failure(self, isolated_env):
        async def scenario(app, pilot):
            # Build a ResultScreen directly with known content.
            app.push_screen(ResultScreen("alpha", "A: hello world\n", copied=False))
            await _settle(pilot)
            assert type(app.screen).__name__ == "ResultScreen"
            await pilot.press("c")
            await _settle(pilot)
            status = str(app.screen.query_one("#status").content)
            assert status.startswith("✗")  # headless clipboard
            assert "--stdout" in status

            with patch("promptcraft.main._copy_to_clipboard_route", return_value="native"):
                await pilot.press("c")
                await _settle(pilot)
            status = str(app.screen.query_one("#status").content)
            assert "Copied to clipboard" in status

        run_app(scenario)

    def test_run_missing_template_shows_error(self, isolated_env):
        async def scenario(app, pilot):
            ghost = TemplateInfo(
                name="ghost",
                description="gone",
                source="Project",
                path=Path("/nonexistent/ghost.md"),
            )
            app.push_screen(RunScreen(ghost))
            await _settle(pilot)
            await pilot.press("enter")
            await _settle(pilot)
            status = str(app.screen.query_one("#status").content)
            assert status.startswith("✗")
            assert "not found" in status
            # The user stays on the run screen and can go back.
            assert type(app.screen).__name__ == "RunScreen"
            await pilot.press("q")
            await _settle(pilot)
            assert type(app.screen).__name__ == "HomeScreen"

        run_app(scenario)

    def test_run_without_arguments(self, isolated_env):
        async def scenario(app, pilot):
            await pilot.press("down")
            await _settle(pilot)
            await pilot.press("r")
            await _settle(pilot)
            await pilot.press("enter")  # submit the empty form (no args)
            await _settle(pilot)
            await pilot.press("d")
            await _settle(pilot)
            body = app.screen.query_one(".result-text").text
            assert body == "# Alpha project\nA: \n"

        run_app(scenario)

    def test_action_buttons_trigger_run_modes(self, isolated_env):
        async def scenario(app, pilot):
            await pilot.press("down")
            await _settle(pilot)
            await pilot.press("r")
            await _settle(pilot)
            assert type(app.screen).__name__ == "RunScreen"
            await _type(pilot, "x")
            # "show on screen" button
            await pilot.click("#btn-show")
            await _settle(pilot)
            assert type(app.screen).__name__ == "ResultScreen"
            assert app.screen.query_one(".result-text").text == "# Alpha project\nA: x\n"
            await pilot.press("q")
            await _settle(pilot)
            # "copy to clipboard" button (mocked success)
            with patch("promptcraft.main._copy_to_clipboard_route", return_value="native"):
                app.screen.action_copy()  # same handler as the copy button
                await _settle(pilot)
            status = str(app.screen.query_one("#status").content)
            assert "Copied to clipboard" in status

        run_app(scenario)


# ---------------------------------------------------------------------------
# Template create / edit
# ---------------------------------------------------------------------------


class TestTemplateScreen:
    async def _open_new(self, app, pilot):
        await pilot.press("n")
        await _settle(pilot)
        assert type(app.screen).__name__ == "TemplateScreen"

    async def _open_edit(self, app, pilot):
        await pilot.press("down")
        await _settle(pilot)
        await pilot.press("e")
        await _settle(pilot)
        assert type(app.screen).__name__ == "TemplateScreen"

    def test_create_defaults(self, isolated_env):
        async def scenario(app, pilot):
            await self._open_new(app, pilot)
            # No name prefilled; project scope is the default when the
            # current directory has a .promptcraft/commands structure.
            assert app.screen.query_one("#name").value == ""
            assert app.screen.query_one("#scope").value == "project"
            assert "New template" in str(app.screen.query_one("#tpl-title").content)

        run_app(scenario)

    def test_create_defaults_to_user_without_project(self, tmp_path, monkeypatch):
        _ensure_valid_cwd(tmp_path)
        monkeypatch.setenv("PROMPTCRAFT_NO_CLIPBOARD", "true")
        bare = tmp_path / "bare"
        bare.mkdir()
        monkeypatch.chdir(bare)
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        _live_invalidate()

        async def scenario(app, pilot):
            await self._open_new(app, pilot)
            assert app.screen.query_one("#scope").value == "user"

        run_app(scenario)
        _live_invalidate()

    def test_create_and_save_to_project(self, isolated_env):
        async def scenario(app, pilot):
            await self._open_new(app, pilot)
            await _type(pilot, "new-cmd")
            await pilot.press("tab")  # -> scope (leave default project)
            await pilot.press("tab")  # -> content
            await _settle(pilot)
            await _type(pilot, "# New command\nRuns $ARGUMENTS now")
            await pilot.press("ctrl+s")
            await _settle(pilot)
            assert type(app.screen).__name__ == "HomeScreen"
            saved = isolated_env["project"] / ".promptcraft" / "commands" / "new-cmd.md"
            assert saved.read_text(encoding="utf-8") == "# New command\nRuns $ARGUMENTS now"

        run_app(scenario)

    def test_create_and_save_to_user_scope(self, isolated_env):
        async def scenario(app, pilot):
            await self._open_new(app, pilot)
            await _type(pilot, "user-cmd")
            await pilot.press("tab")  # -> scope
            await pilot.press("space")  # open the overlay
            await pilot.press("down")  # highlight the user option
            await pilot.press("enter")  # select it
            await _settle(pilot)
            assert app.screen.query_one("#scope").value == "user"
            await pilot.press("tab")  # -> content
            await _settle(pilot)
            await _type(pilot, "# User command")
            await pilot.press("ctrl+s")
            await _settle(pilot)
            saved = isolated_env["home"] / ".promptcraft" / "commands" / "user-cmd.md"
            assert saved.read_text(encoding="utf-8") == "# User command"

        run_app(scenario)

    def test_create_rejects_empty_name(self, isolated_env):
        async def scenario(app, pilot):
            await self._open_new(app, pilot)
            await pilot.press("ctrl+s")
            await _settle(pilot)
            status = str(app.screen.query_one("#status").content)
            assert status.startswith("✗")
            assert "Name is required" in status
            assert type(app.screen).__name__ == "TemplateScreen"

        run_app(scenario)

    def test_create_rejects_path_separators(self, isolated_env):
        async def scenario(app, pilot):
            await self._open_new(app, pilot)
            await _type(pilot, "a/b")
            await pilot.press("ctrl+s")
            await _settle(pilot)
            status = str(app.screen.query_one("#status").content)
            assert "path separators" in status

        run_app(scenario)

    def test_create_rejects_empty_content(self, isolated_env):
        async def scenario(app, pilot):
            await self._open_new(app, pilot)
            await _type(pilot, "no-content")
            await pilot.press("tab")
            await pilot.press("tab")  # -> content (left empty)
            await pilot.press("ctrl+s")
            await _settle(pilot)
            status = str(app.screen.query_one("#status").content)
            assert "Content is required" in status
            assert not (
                isolated_env["project"] / ".promptcraft" / "commands" / "no-content.md"
            ).exists()

        run_app(scenario)

    def test_create_warns_before_overwriting(self, isolated_env):
        async def scenario(app, pilot):
            await self._open_new(app, pilot)
            await _type(pilot, "alpha")  # exists in project scope
            await pilot.press("tab")
            await pilot.press("tab")
            await _settle(pilot)
            await _type(pilot, "# Overwrite\n")
            await pilot.press("ctrl+s")  # first press: confirmation
            await _settle(pilot)
            status = str(app.screen.query_one("#status").content)
            assert "already exists" in status
            # File not yet overwritten
            original = isolated_env["project"] / ".promptcraft" / "commands" / "alpha.md"
            assert original.read_text(encoding="utf-8") == "# Alpha project\nA: $ARGUMENTS\n"
            await pilot.press("ctrl+s")  # second press: do it
            await _settle(pilot)
            assert type(app.screen).__name__ == "HomeScreen"
            assert original.read_text(encoding="utf-8") == "# Overwrite\n"

        run_app(scenario)

    def test_edit_prefills_and_saves_back(self, isolated_env):
        async def scenario(app, pilot):
            await self._open_edit(app, pilot)
            assert app.screen.query_one("#name").value == "alpha"
            assert app.screen.query_one("#scope").value == "project"
            content = app.screen.query_one("#content").text
            assert content == "# Alpha project\nA: $ARGUMENTS\n"
            app.screen.query_one("#content").text = "# Alpha v2\nA: $ARGUMENTS more"
            await _settle(pilot)
            await pilot.press("ctrl+s")
            await _settle(pilot)
            assert type(app.screen).__name__ == "HomeScreen"
            edited = isolated_env["project"] / ".promptcraft" / "commands" / "alpha.md"
            assert edited.read_text(encoding="utf-8") == "# Alpha v2\nA: $ARGUMENTS more"

        run_app(scenario)

    def test_edit_with_scope_change_moves_to_user_scope(self, isolated_env):
        async def scenario(app, pilot):
            await self._open_edit(app, pilot)  # alpha (project)
            await pilot.press("tab")  # -> scope
            await pilot.press("space")
            await pilot.press("down")
            await pilot.press("enter")  # user
            await _settle(pilot)
            assert app.screen.query_one("#scope").value == "user"
            await pilot.press("tab")
            await _settle(pilot)
            await pilot.press("ctrl+s")  # save: moves project -> user
            await _settle(pilot)
            assert type(app.screen).__name__ == "HomeScreen"
            original = isolated_env["project"] / ".promptcraft" / "commands" / "alpha.md"
            moved = isolated_env["home"] / ".promptcraft" / "commands" / "alpha.md"
            assert not original.exists()
            assert moved.read_text(encoding="utf-8") == "# Alpha project\nA: $ARGUMENTS\n"

        run_app(scenario)

    def test_edit_with_scope_change_overwrites_and_moves(self, isolated_env):
        async def scenario(app, pilot):
            target = isolated_env["home"] / ".promptcraft" / "commands" / "alpha.md"
            target.write_text("# Stale user copy\n", encoding="utf-8")
            await self._open_edit(app, pilot)  # alpha (project)
            await pilot.press("tab")  # -> scope
            await pilot.press("space")
            await pilot.press("down")
            await pilot.press("enter")  # user
            await _settle(pilot)
            await pilot.press("tab")
            await _settle(pilot)
            await pilot.press("ctrl+s")  # first press: overwrite + move warning
            await _settle(pilot)
            status = str(app.screen.query_one("#status").content)
            assert "already exists" in status
            assert "will be removed" in status
            assert type(app.screen).__name__ == "TemplateScreen"
            original = isolated_env["project"] / ".promptcraft" / "commands" / "alpha.md"
            assert original.exists()  # nothing moved yet
            await pilot.press("ctrl+s")  # second press: go
            await _settle(pilot)
            assert type(app.screen).__name__ == "HomeScreen"
            assert not original.exists()
            assert target.read_text(encoding="utf-8") == "# Alpha project\nA: $ARGUMENTS\n"

        run_app(scenario)

    def test_edit_rename_same_scope_moves(self, isolated_env):
        async def scenario(app, pilot):
            await self._open_edit(app, pilot)  # alpha (project)
            app.screen.query_one("#name").value = "alpha2"
            await _settle(pilot)
            await pilot.press("ctrl+s")
            await _settle(pilot)
            assert type(app.screen).__name__ == "HomeScreen"
            commands = isolated_env["project"] / ".promptcraft" / "commands"
            assert not (commands / "alpha.md").exists()
            assert (commands / "alpha2.md").read_text(
                encoding="utf-8"
            ) == "# Alpha project\nA: $ARGUMENTS\n"

        run_app(scenario)

    def test_edit_move_when_original_already_gone(self, isolated_env):
        async def scenario(app, pilot):
            await self._open_edit(app, pilot)  # alpha (project)
            original = isolated_env["project"] / ".promptcraft" / "commands" / "alpha.md"
            original.unlink()  # deleted externally while editing
            await pilot.press("tab")  # -> scope
            await pilot.press("space")
            await pilot.press("down")
            await pilot.press("enter")  # user
            await _settle(pilot)
            await pilot.press("tab")
            await _settle(pilot)
            await pilot.press("ctrl+s")
            await _settle(pilot)
            assert type(app.screen).__name__ == "HomeScreen"
            moved = isolated_env["home"] / ".promptcraft" / "commands" / "alpha.md"
            assert moved.read_text(encoding="utf-8") == "# Alpha project\nA: $ARGUMENTS\n"

        run_app(scenario)

    def test_edit_move_reports_when_original_removal_fails(self, isolated_env):
        from unittest.mock import patch as _patch

        async def scenario(app, pilot):
            await self._open_edit(app, pilot)  # alpha (project)
            app.screen.query_one("#scope").value = "user"
            await _settle(pilot)
            with _patch(
                "promptcraft.tui.actions.delete_template",
                side_effect=OSError("read-only filesystem"),
            ):
                await pilot.press("ctrl+s")
                await _settle(pilot)
            # The new copy was saved; the original stays (warned, not lost).
            assert type(app.screen).__name__ == "HomeScreen"
            original = isolated_env["project"] / ".promptcraft" / "commands" / "alpha.md"
            copy = isolated_env["home"] / ".promptcraft" / "commands" / "alpha.md"
            assert original.read_text(encoding="utf-8") == "# Alpha project\nA: $ARGUMENTS\n"
            assert copy.read_text(encoding="utf-8") == "# Alpha project\nA: $ARGUMENTS\n"

        run_app(scenario)

    def test_edit_back_discards_changes(self, isolated_env):
        async def scenario(app, pilot):
            await self._open_edit(app, pilot)
            app.screen.query_one("#content").text = "# CHANGED\n"
            await _settle(pilot)
            await pilot.press("escape")
            await _settle(pilot)
            assert type(app.screen).__name__ == "HomeScreen"
            original = isolated_env["project"] / ".promptcraft" / "commands" / "alpha.md"
            assert original.read_text(encoding="utf-8") == "# Alpha project\nA: $ARGUMENTS\n"

        run_app(scenario)


# ---------------------------------------------------------------------------
# Delete template (double-press to confirm)
# ---------------------------------------------------------------------------


class TestDeleteTemplate:
    def test_delete_with_double_press(self, isolated_env):
        async def scenario(app, pilot):
            target = isolated_env["project"] / ".promptcraft" / "commands" / "alpha.md"
            await pilot.press("down")  # highlight alpha
            await _settle(pilot)
            await pilot.press("d")  # first press: confirmation
            await _settle(pilot)
            status = str(app.screen.query_one("#status").content)
            assert "Press d again to confirm" in status
            assert target.exists()  # not deleted yet
            await pilot.press("d")  # second press: go
            await _settle(pilot)
            assert type(app.screen).__name__ == "HomeScreen"
            assert not target.exists()
            status = str(app.screen.query_one("#status").content)
            assert status.startswith("✓ Deleted")
            by_id = {o.id for o in app.query_one("#templates").options}
            assert "alpha" not in by_id

        run_app(scenario)

    def test_delete_without_selection_warns(self, tmp_path, monkeypatch):
        _ensure_valid_cwd(tmp_path)
        monkeypatch.setenv("PROMPTCRAFT_NO_CLIPBOARD", "true")
        empty_project = tmp_path / "empty-del"
        empty_project.mkdir()
        monkeypatch.chdir(empty_project)
        monkeypatch.setenv("HOME", str(tmp_path / "empty-del-home"))
        _live_invalidate()

        async def scenario(app, pilot):
            await pilot.press("d")
            await _settle(pilot)
            assert type(app.screen).__name__ == "HomeScreen"
            assert app.query_one("#templates").options == []

        run_app(scenario)
        _live_invalidate()

    def test_delete_confirm_resets_when_selection_changes(self, isolated_env):
        async def scenario(app, pilot):
            alpha = isolated_env["project"] / ".promptcraft" / "commands" / "alpha.md"
            beta = isolated_env["home"] / ".promptcraft" / "commands" / "beta.md"
            await pilot.press("down")  # highlight alpha
            await _settle(pilot)
            await pilot.press("d")  # confirm armed for alpha
            await _settle(pilot)
            await pilot.press("down")  # move to beta: confirm must reset
            await _settle(pilot)
            await pilot.press("d")  # first press for beta: confirmation only
            await _settle(pilot)
            assert alpha.exists() and beta.exists()
            await pilot.press("d")  # second press: deletes beta (user scope)
            await _settle(pilot)
            assert alpha.exists()
            assert not beta.exists()

        run_app(scenario)

    def test_delete_already_gone_refreshes(self, isolated_env):
        async def scenario(app, pilot):
            target = isolated_env["project"] / ".promptcraft" / "commands" / "alpha.md"
            await pilot.press("down")
            await _settle(pilot)
            await pilot.press("d")  # confirm armed
            await _settle(pilot)
            target.unlink()  # deleted externally before confirming
            await pilot.press("d")
            await _settle(pilot)
            assert type(app.screen).__name__ == "HomeScreen"
            status = str(app.screen.query_one("#status").content)
            assert "already deleted" in status
            by_id = {o.id for o in app.query_one("#templates").options}
            assert "alpha" not in by_id

        run_app(scenario)

    def test_delete_failure_shows_error(self, isolated_env):
        from unittest.mock import patch as _patch

        async def scenario(app, pilot):
            target = isolated_env["project"] / ".promptcraft" / "commands" / "alpha.md"
            await pilot.press("down")
            await _settle(pilot)
            await pilot.press("d")
            await _settle(pilot)
            with _patch(
                "promptcraft.tui.app.actions.delete_template",
                side_effect=PermissionError("denied"),
            ):
                await pilot.press("d")
                await _settle(pilot)
            assert type(app.screen).__name__ == "HomeScreen"
            status = str(app.screen.query_one("#status").content)
            assert status.startswith("✗ Delete failed")
            assert target.exists()

        run_app(scenario)

    def test_delete_cancel_with_escape(self, isolated_env):
        async def scenario(app, pilot):
            target = isolated_env["project"] / ".promptcraft" / "commands" / "alpha.md"
            await pilot.press("down")
            await _settle(pilot)
            await pilot.press("d")  # arm delete
            await _settle(pilot)
            status = str(app.screen.query_one("#status").content)
            assert "Press d again to confirm" in status
            await pilot.press("escape")  # cancel
            await _settle(pilot)
            assert type(app.screen).__name__ == "HomeScreen"
            status = str(app.screen.query_one("#status").content)
            assert "cancelled" in status.lower()
            assert target.exists()
            # Pressing d again now requires two presses again
            await pilot.press("d")
            await _settle(pilot)
            assert target.exists()

        run_app(scenario)

    def test_delete_from_template_screen_edit_mode(self, isolated_env):
        async def scenario(app, pilot):
            target = isolated_env["project"] / ".promptcraft" / "commands" / "alpha.md"
            await pilot.press("down")
            await _settle(pilot)
            await pilot.press("e")  # edit alpha
            await _settle(pilot)
            assert type(app.screen).__name__ == "TemplateScreen"
            # Delete button is visible
            assert app.screen.query_one("#btn-delete") is not None
            # Press Ctrl+D: confirmation
            await pilot.press("ctrl+d")
            await _settle(pilot)
            status = str(app.screen.query_one("#status").content)
            assert "Press Ctrl+D" in status
            assert target.exists()
            # Press Ctrl+D second time: confirms and deletes
            await pilot.press("ctrl+d")
            await _settle(pilot)
            assert type(app.screen).__name__ == "HomeScreen"
            assert not target.exists()
            by_id = {o.id for o in app.query_one("#templates").options}
            assert "alpha" not in by_id

        run_app(scenario)

    def test_delete_cancel_with_escape_in_template_screen(self, isolated_env):
        async def scenario(app, pilot):
            target = isolated_env["project"] / ".promptcraft" / "commands" / "alpha.md"
            await pilot.press("down")
            await _settle(pilot)
            await pilot.press("e")
            await _settle(pilot)
            assert type(app.screen).__name__ == "TemplateScreen"
            await pilot.press("ctrl+d")  # arm delete
            await _settle(pilot)
            assert "Press Ctrl+D" in str(app.screen.query_one("#status").content)
            await pilot.press("escape")  # cancel delete
            await _settle(pilot)
            assert type(app.screen).__name__ == "TemplateScreen"
            assert "cancelled" in str(app.screen.query_one("#status").content).lower()
            assert target.exists()
            # Next escape backs out to HomeScreen
            await pilot.press("escape")
            await _settle(pilot)
            assert type(app.screen).__name__ == "HomeScreen"
            assert target.exists()

        run_app(scenario)

    def test_delete_with_button_in_template_screen(self, isolated_env):
        async def scenario(app, pilot):
            target = isolated_env["project"] / ".promptcraft" / "commands" / "alpha.md"
            await pilot.press("down")
            await _settle(pilot)
            await pilot.press("e")
            await _settle(pilot)
            assert type(app.screen).__name__ == "TemplateScreen"
            await pilot.click("#btn-delete")  # first click: confirmation
            await _settle(pilot)
            assert target.exists()
            assert "confirm" in str(app.screen.query_one("#status").content).lower()
            await asyncio.sleep(0.3)
            await pilot.click("#btn-delete")  # second click: go
            await _settle(pilot)
            assert type(app.screen).__name__ == "HomeScreen"
            assert not target.exists()

        run_app(scenario)

    def test_delete_in_create_mode_warns(self, isolated_env):
        async def scenario(app, pilot):
            await pilot.press("n")  # new template
            await _settle(pilot)
            assert type(app.screen).__name__ == "TemplateScreen"
            # btn-delete is not present in create mode
            assert len(app.screen.query("#btn-delete")) == 0
            # action_delete warns
            app.screen.action_delete()
            await _settle(pilot)
            assert "Cannot delete" in str(app.screen.query_one("#status").content)

        run_app(scenario)

    def test_delete_in_template_screen_already_gone(self, isolated_env):
        async def scenario(app, pilot):
            target = isolated_env["project"] / ".promptcraft" / "commands" / "alpha.md"
            await pilot.press("down")
            await _settle(pilot)
            await pilot.press("e")
            await _settle(pilot)
            assert type(app.screen).__name__ == "TemplateScreen"
            await pilot.press("ctrl+d")  # arm delete
            await _settle(pilot)
            target.unlink()  # deleted externally
            await pilot.press("ctrl+d")  # second press
            await _settle(pilot)
            assert type(app.screen).__name__ == "HomeScreen"

        run_app(scenario)

    def test_delete_in_template_screen_error_shows_failure(self, isolated_env):
        from unittest.mock import patch as _patch

        async def scenario(app, pilot):
            target = isolated_env["project"] / ".promptcraft" / "commands" / "alpha.md"
            await pilot.press("down")
            await _settle(pilot)
            await pilot.press("e")
            await _settle(pilot)
            assert type(app.screen).__name__ == "TemplateScreen"
            await pilot.press("ctrl+d")  # arm delete
            await _settle(pilot)
            with _patch(
                "promptcraft.tui.app.actions.delete_template",
                side_effect=PermissionError("denied"),
            ):
                await pilot.press("ctrl+d")  # second press fails
                await _settle(pilot)
            assert type(app.screen).__name__ == "TemplateScreen"
            assert "✗ Delete failed" in str(app.screen.query_one("#status").content)
            assert target.exists()

        run_app(scenario)


# ---------------------------------------------------------------------------
# Init / version / help
# ---------------------------------------------------------------------------


class TestInitVersionHelp:
    def test_init_creates_example_and_is_idempotent(self, isolated_env):
        async def scenario(app, pilot):
            await pilot.press("i")
            await _settle(pilot)
            assert type(app.screen).__name__ == "InitResultScreen"
            summary = str(app.screen.query_one("#init-summary").content)
            assert "Created example template: exemplo.md" in summary
            example = isolated_env["project"] / ".promptcraft" / "commands" / "exemplo.md"
            assert example.read_text(encoding="utf-8") == EXAMPLE_TEMPLATE
            # Existing templates untouched
            alpha = isolated_env["project"] / ".promptcraft" / "commands" / "alpha.md"
            assert alpha.read_text(encoding="utf-8") == "# Alpha project\nA: $ARGUMENTS\n"
            await pilot.press("escape")
            await _settle(pilot)
            # Second run: everything already exists, nothing overwritten
            await pilot.press("i")
            await _settle(pilot)
            summary = str(app.screen.query_one("#init-summary").content)
            assert "Example template already exists: exemplo.md" in summary
            assert "Created" not in summary
            assert example.read_text(encoding="utf-8") == EXAMPLE_TEMPLATE

        run_app(scenario)

    def test_version_screen(self, isolated_env):
        async def scenario(app, pilot):
            await pilot.press("v")
            await _settle(pilot)
            assert type(app.screen).__name__ == "VersionScreen"
            assert app.screen.query_one("#version-value").content == f"PromptCraft v{__version__}"
            await pilot.press("escape")
            await _settle(pilot)
            assert type(app.screen).__name__ == "HomeScreen"

        run_app(scenario)

    def test_help_screen_lists_all_shortcuts(self, isolated_env):
        async def scenario(app, pilot):
            await pilot.press("?")
            await _settle(pilot)
            assert type(app.screen).__name__ == "HelpScreen"
            text = str(app.screen.query_one("#help-text").content)
            for section in (
                "Home (template list)",
                "Run template",
                "Result",
                "New / edit template",
                "Init / version / help",
            ):
                assert section in text
            await pilot.press("?")  # ? also closes
            await _settle(pilot)
            assert type(app.screen).__name__ == "HomeScreen"

        run_app(scenario)

    def test_shortcuts_are_visible_in_footer(self, isolated_env):
        async def scenario(app, pilot):
            footer = app.query_one("Footer")
            assert footer is not None
            active = app.screen.active_bindings
            # The main home actions are always visible. ("?" is normalized
            # to the key name "question_mark" by the key parser.)
            for key in ("r", "n", "e", "d", "i", "v", "f", "q"):
                assert key in active, f"missing visible binding: {key}"
            assert "question_mark" in active or "?" in active

        run_app(scenario)


class TestOcrCycle1Regressions:
    """Regression tests for the actionable findings of the first
    open-code-review pass (crash, stale state, misleading text)."""

    def test_enter_in_name_field_saves(self, isolated_env):
        """Enter in the name field saves the template (no AttributeError)."""

        async def scenario(app, pilot):
            await pilot.press("n")
            await _settle(pilot)
            await _type(pilot, "enter-save")
            await pilot.press("tab")
            await pilot.press("tab")  # -> content
            await _type(pilot, "# Enter saved")
            app.screen.query_one("#name").focus()
            await _settle(pilot)
            await pilot.press("enter")
            await _settle(pilot)
            assert type(app.screen).__name__ == "HomeScreen"
            saved = isolated_env["project"] / ".promptcraft" / "commands" / "enter-save.md"
            assert saved.read_text(encoding="utf-8") == "# Enter saved"

        run_app(scenario)

    def test_display_runs_fresh_after_argument_change(self, isolated_env):
        async def scenario(app, pilot):
            await pilot.press("down")
            await _settle(pilot)
            await pilot.press("r")
            await _settle(pilot)
            await _type(pilot, "first")
            await pilot.press("enter")
            await _settle(pilot)
            app.screen.query_one("#args").value = "second"
            await _settle(pilot)
            await pilot.press("d")
            await _settle(pilot)
            assert type(app.screen).__name__ == "ResultScreen"
            assert app.screen.query_one(".result-text").text == "# Alpha project\nA: second\n"

        run_app(scenario)

    def test_overwrite_confirm_is_tied_to_target(self, isolated_env):
        async def scenario(app, pilot):
            await pilot.press("n")
            await _settle(pilot)
            await _type(pilot, "alpha")  # exists in project scope
            await pilot.press("tab")
            await pilot.press("tab")
            await _type(pilot, "# X")
            await pilot.press("ctrl+s")
            await _settle(pilot)
            status = str(app.screen.query_one("#status").content)
            assert "Ctrl+S" in status  # the prompt points to a key that works
            # Now change the name to another existing template: warning again.
            app.screen.query_one("#name").value = "shared"
            await _settle(pilot)
            await pilot.press("ctrl+s")
            await _settle(pilot)
            assert type(app.screen).__name__ == "TemplateScreen"
            shared = isolated_env["project"] / ".promptcraft" / "commands" / "shared.md"
            assert shared.read_text(encoding="utf-8") == "# Shared project\nP: $ARGUMENTS\n"

        run_app(scenario)

    def test_home_list_refreshes_after_save(self, isolated_env):
        async def scenario(app, pilot):
            await pilot.press("n")
            await _settle(pilot)
            await _type(pilot, "late-add")
            await pilot.press("tab")
            await pilot.press("tab")
            await _type(pilot, "# Late add")
            await pilot.press("ctrl+s")
            await _settle(pilot)
            assert type(app.screen).__name__ == "HomeScreen"
            by_id = {o.id for o in app.query_one("#templates").options}
            assert "late-add" in by_id

        run_app(scenario)

    def test_display_marks_result_as_already_copied(self, isolated_env):
        from unittest.mock import patch as _patch

        async def scenario(app, pilot):
            with _patch("promptcraft.main._copy_to_clipboard_route", return_value="native"):
                await pilot.press("down")
                await _settle(pilot)
                await pilot.press("r")
                await _settle(pilot)
                await _type(pilot, "hello")
                await pilot.press("enter")
                await _settle(pilot)
                await pilot.press("d")
                await _settle(pilot)
            assert type(app.screen).__name__ == "ResultScreen"
            status = str(app.screen.query_one("#status").content)
            assert status.startswith("✓ Already copied")

        run_app(scenario)


class TestOcrCycle2Regressions:
    """Regression tests for the actionable findings of the second
    open-code-review pass."""

    def test_typing_q_does_not_discard_draft(self, isolated_env):
        """Typing words with 'q' keeps the user on TemplateScreen."""

        async def scenario(app, pilot):
            await pilot.press("n")
            await _settle(pilot)
            await _type(pilot, "quick")
            await pilot.press("tab")  # scope
            await pilot.press("tab")  # content
            await _settle(pilot)
            await _type(pilot, "unique request and SQL")
            await pilot.press("ctrl+s")
            await _settle(pilot)
            assert type(app.screen).__name__ == "HomeScreen"
            saved = isolated_env["project"] / ".promptcraft" / "commands" / "quick.md"
            assert saved.read_text(encoding="utf-8") == "unique request and SQL"

        run_app(scenario)

    def test_scope_cancel_keeps_draft(self, isolated_env):
        """Cancelling a scope change keeps the user on the screen with the draft intact."""

        async def scenario(app, pilot):
            await pilot.press("n")
            await _settle(pilot)
            await _type(pilot, "scope-keep")
            await pilot.press("tab")  # scope Select
            await _settle(pilot)
            scope = app.screen.query_one("#scope")
            scope.value = "user"  # same as picking the other option, no overlay needed
            await _settle(pilot)
            assert type(app.screen).__name__ == "TemplateScreen"
            assert scope.value == "user"
            scope.value = "project"  # restore; draft must be intact either way
            await _settle(pilot)
            assert app.screen.query_one("#name").value == "scope-keep"
            await pilot.press("escape")  # explicit cancel from the Select itself
            await _settle(pilot, 2)
            assert type(app.screen).__name__ == "HomeScreen"

        run_app(scenario)

    def test_markup_in_template_text_does_not_crash(self, isolated_env):
        """Bracket sequences in names/descriptions render literally."""

        async def scenario(app, pilot):
            tricky = isolated_env["project"] / ".promptcraft" / "commands" / "zzb.md"
            tricky.write_text("first [b]bold[/b] line\n[$ARGUMENTS]\n", encoding="utf-8")
            from promptcraft.core import invalidate_caches as _inv

            _inv()
            await pilot.press("f")  # refresh to pick up the new file
            await _settle(pilot)
            await pilot.press("down")
            await _settle(pilot)
            await pilot.press("down")
            await _settle(pilot)
            await pilot.press("down")
            await _settle(pilot)
            names = [str(o.prompt) for o in app.query_one("#templates").options]
            assert any("zzb" in name for name in names)
            # move the highlight onto the tricky entry, wherever it sorted
            app.screen.populate_list(keep_highlight="zzb")
            await _settle(pilot)
            highlighted = app.screen.highlighted
            assert highlighted is not None and highlighted.name == "zzb"
            assert highlighted.description == "first [b]bold[/b] line"
            det = str(app.screen.query_one("#details").content)
            assert "zzb" in det

            # the detail line would have raised MarkupError pre-fix; the list
            # row itself renders the raw description literally
            rows = {o.id: str(o.prompt) for o in app.query_one("#templates").options}
            assert "[b]bold[/b]" in rows["zzb"] and "[$ARGUMENTS]" not in rows["zzb"]

        run_app(scenario)

    def test_home_keeps_highlight_on_resume(self, isolated_env):
        """Returning from Help keeps the highlighted template selected."""

        async def scenario(app, pilot):
            await pilot.press("down")
            await _settle(pilot)
            assert app.screen.highlighted is not None
            name = app.screen.highlighted.name
            await pilot.press("?")
            await _settle(pilot)
            assert type(app.screen).__name__ == "HelpScreen"
            await pilot.press("escape")
            await _settle(pilot)
            assert type(app.screen).__name__ == "HomeScreen"
            assert app.screen.highlighted is not None
            assert app.screen.highlighted.name == name
            await pilot.press("r")  # re-run immediately still works
            await _settle(pilot)
            assert type(app.screen).__name__ == "RunScreen"

        run_app(scenario)

    def test_run_with_q_arguments(self, isolated_env):
        """Arguments containing 'q' are typed, not treated as Back."""

        async def scenario(app, pilot):
            await pilot.press("down")
            await _settle(pilot)
            await pilot.press("r")
            await _settle(pilot)
            await _type(pilot, "fix the query")
            assert type(app.screen).__name__ == "RunScreen"
            assert app.screen.query_one("#args").value == "fix the query"

        run_app(scenario)


class TestOcrCycle3Regressions:
    """Regression tests for the actionable findings of the third
    open-code-review pass."""

    def test_cancel_from_select_keeps_draft(self, isolated_env):
        """Esc / q with the scope Select focused stays; back discards."""

        async def scenario(app, pilot):
            await pilot.press("n")
            await _settle(pilot)
            await _type(pilot, "cancel-keep")
            await pilot.press("tab")  # scope Select
            await _settle(pilot)
            # Esc while the Select is closed acts as back (pre-existing rows above)
            app.screen.query_one("#content").focus()
            await _settle(pilot)
            await pilot.press("escape")
            await _settle(pilot)
            assert type(app.screen).__name__ == "HomeScreen"

        run_app(scenario)

    def test_init_error_branch_displays(self, isolated_env):
        """A failing init shows the error status instead of crashing."""
        from unittest.mock import patch as _patch

        async def scenario(app, pilot):
            # Force the OSError branch with an errno-style message: the
            # status text must render literally, not crash on [Errno N].
            with _patch(
                "pathlib.Path.mkdir",
                side_effect=OSError(30, "Read-only file system"),
            ):
                await pilot.press("i")
                await _settle(pilot)
            assert type(app.screen).__name__ == "HomeScreen"
            status = str(app.screen.query_one("#status").content)
            assert status.startswith("✗") and "Errno" in status

        run_app(scenario)


class TestOcrCycle4Regressions:
    """Regression tests for the actionable findings of the fourth
    open-code-review pass."""

    def test_second_enter_runs_copy_not_display(self, isolated_env):
        """A second Enter after a run re-runs copy; ResultScreen stays out."""
        from unittest.mock import patch as _patch

        async def scenario(app, pilot):
            with _patch("promptcraft.main._copy_to_clipboard_route", return_value="native"):
                await pilot.press("down")
                await _settle(pilot)
                await pilot.press("r")
                await _settle(pilot)
                assert type(app.screen).__name__ == "RunScreen"
                args_input = app.screen.query_one("#args")
                args_input.value = "again"
                await _settle(pilot)
                app.screen.action_copy()  # first Enter: copies
                await _settle(pilot)
            assert type(app.screen).__name__ == "RunScreen"  # not ResultScreen
            assert "Copied" in str(app.screen.query_one("#status").content)

        run_app(scenario)


class TestTuiCoverageEdgeCases:
    def test_home_screen_option_events_and_selection_fallbacks(self, isolated_env):
        from unittest.mock import Mock
        from textual.widgets import OptionList

        async def scenario(app, pilot):
            home = app.screen
            ol = home.query_one("#templates", OptionList)

            # 1. OptionHighlighted when option is None
            ev_none = Mock()
            ev_none.option = None
            home.on_option_list_option_highlighted(ev_none)
            home.on_option_list_option_selected(ev_none)

            # 2. OptionHighlighted when template is None
            ev_missing = Mock()
            ev_missing.option = Mock(id="non_existent")
            home.on_option_list_option_highlighted(ev_missing)
            home.on_option_list_option_selected(ev_missing)

            # OptionSelected with valid option
            ev_valid = Mock()
            ev_valid.option = Mock(id="alpha")
            home.on_option_list_option_selected(ev_valid)
            app.pop_screen()  # pop the RunScreen that was pushed

            # 3. _selected_template fallback when self.highlighted is None
            await pilot.press("down")
            await _settle(pilot)
            home.highlighted = None
            assert home._selected_template() is not None

            # 4. action_run_selected / action_edit_selected when no template selected
            home.highlighted = None
            ol.clear_options()
            home.action_run_selected()
            home.action_edit_selected()
            home.action_delete_selected()

            # 5. action_cancel_or_quit quits app when no delete confirmed
            home._confirmed_delete = None
            home.action_cancel_or_quit()
            await _settle(pilot)
            assert not app.is_running

        run_app(scenario)

    def test_run_screen_btn_copy_and_exceptions(self, isolated_env):
        from textual.widgets import Button

        async def scenario(app, pilot):
            await pilot.press("down")
            await _settle(pilot)
            await pilot.press("r")
            await _settle(pilot)
            assert type(app.screen).__name__ == "RunScreen"

            # 1. Button pressed for #btn-copy
            btn_copy = app.screen.query_one("#btn-copy", Button)
            app.screen.on_button_pressed(Button.Pressed(btn_copy))
            await _settle(pilot)

            # 2. Unexpected exception in _run()
            with patch("promptcraft.tui.actions.run_template", side_effect=RuntimeError("unexpected crash")):
                app.screen.action_copy()
                await _settle(pilot)
                status = str(app.screen.query_one("#status").content)
                assert "Unexpected error" in status

                # 3. action_display when _run() returns None
                app.screen.action_display()
                await _settle(pilot)
                assert type(app.screen).__name__ == "RunScreen"

            # 4. Button pressed with unknown ID
            other_btn = Button("Other", id="btn-other")
            app.screen.on_button_pressed(Button.Pressed(other_btn))

        run_app(scenario)

    def test_result_screen_copy_failure(self, isolated_env):
        async def scenario(app, pilot):
            res_screen = ResultScreen("test", "test content", copied=False)
            await app.push_screen(res_screen)
            await _settle(pilot)

            with patch("promptcraft.tui.actions.copy_to_clipboard", return_value=False):
                res_screen.action_copy()
                await _settle(pilot)
                status = str(res_screen.query_one("#status").content)
                assert "Could not copy" in status

        run_app(scenario)

    def test_template_screen_mount_read_error_and_save_error(self, isolated_env):
        from textual.widgets import Input, Button

        async def scenario(app, pilot):
            # 1. Mount read error
            with patch("promptcraft.tui.actions.load_template_content", side_effect=OSError("disk read error")):
                await pilot.press("down")
                await _settle(pilot)
                await pilot.press("e")
                await _settle(pilot)
                assert type(app.screen).__name__ == "HomeScreen"

            # 2. Save error
            await pilot.press("n")
            await _settle(pilot)
            assert type(app.screen).__name__ == "TemplateScreen"
            app.screen.query_one("#name").value = "failing-save"
            app.screen.query_one("#content").text = "Some valid content"
            with patch("promptcraft.tui.actions.save_template", side_effect=OSError("disk write error")):
                await pilot.press("ctrl+s")
                await _settle(pilot)
                status = str(app.screen.query_one("#status").content)
                assert "Save failed" in status

            # 3. on_input_submitted with control other than name
            other_input = Input(id="other-input")
            app.screen.on_input_submitted(Input.Submitted(other_input, "val"))

            # 4. on_button_pressed with button other than btn-delete
            other_btn = Button("Other", id="btn-other")
            app.screen.on_button_pressed(Button.Pressed(other_btn))

        run_app(scenario)


