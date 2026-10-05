"""Unit tests for the PromptCraft TUI action layer.

The action layer is the contract between the interactive UI and the
existing CLI logic: everything here must behave exactly like the command
line (same discovery, same processing, same clipboard handling, same
idempotent init).
"""

import importlib
import os
from pathlib import Path

import pytest

from promptcraft import __version__
from promptcraft.exceptions import CommandNotFoundError, TemplateReadError
from promptcraft.example_template import EXAMPLE_TEMPLATE
from promptcraft.tui import actions
from promptcraft.tui.actions import (
    InitResult,
    TemplateInfo,
    delete_template,
    list_templates,
    normalize_name,
    run_template,
    save_template,
    validate_template_name,
)


def _ensure_valid_cwd(tmp_path):
    """The pre-existing broken tests can leave the process CWD in a deleted
    directory. Escape it first (an absolute os.chdir never reads the old
    CWD) so a subsequent monkeypatch.chdir() can record a restore point."""
    try:
        os.getcwd()
    except OSError:
        os.chdir(str(tmp_path))


@pytest.fixture(autouse=True)
def clean_discovery_cache(tmp_path, monkeypatch):
    """Each test starts and ends with a fresh discovery/path cache and an
    isolated HOME (so the real user's ~/.promptcraft never leaks in).

    Benchmark tests purge promptcraft.* from sys.modules and re-import, so
    names bound at collection time can point at detached module copies with
    their own caches and exception classes. Everything core-related is
    therefore resolved through the live registry, per test.
    """
    _ensure_valid_cwd(tmp_path)
    core = importlib.import_module("promptcraft.core")
    exceptions = importlib.import_module("promptcraft.exceptions")
    globals()["CommandNotFoundError"] = exceptions.CommandNotFoundError
    globals()["TemplateReadError"] = exceptions.TemplateReadError
    core.invalidate_caches()
    monkeypatch.setenv("HOME", str(tmp_path / "isolated-home"))
    yield
    importlib.import_module("promptcraft.core").invalidate_caches()


@pytest.fixture
def project_dir(tmp_path, monkeypatch):
    """A temp project directory with a .promptcraft/commands structure."""
    project = tmp_path / "project"
    commands = project / ".promptcraft" / "commands"
    commands.mkdir(parents=True)
    (commands / "alpha.md").write_text("# Alpha project\nA: $ARGUMENTS\n", encoding="utf-8")
    (commands / "shared.md").write_text("# Shared project\nP: $ARGUMENTS\n", encoding="utf-8")
    monkeypatch.chdir(project)
    return project


@pytest.fixture
def user_dir(tmp_path, monkeypatch):
    """A temp user home with a ~/.promptcraft/commands structure."""
    home = tmp_path / "home"
    commands = home / ".promptcraft" / "commands"
    commands.mkdir(parents=True)
    (commands / "beta.md").write_text("# Beta user\nB: $ARGUMENTS\n", encoding="utf-8")
    (commands / "shared.md").write_text("# Shared user\nU: $ARGUMENTS\n", encoding="utf-8")
    monkeypatch.setenv("HOME", str(home))
    return home


# ---------------------------------------------------------------------------
# Discovery (list_templates)
# ---------------------------------------------------------------------------


class TestListTemplates:
    def test_finds_project_and_user_templates(self, project_dir, user_dir):
        templates = list_templates()
        names = [t.name for t in templates]
        assert names == ["alpha", "beta", "shared"]  # sorted, deduped

    def test_project_wins_on_name_conflict(self, project_dir, user_dir):
        templates = {t.name: t for t in list_templates()}
        assert templates["shared"].source == "Project"
        assert str(templates["shared"].path).startswith(str(project_dir))

    def test_description_is_first_line(self, project_dir, user_dir):
        templates = {t.name: t for t in list_templates()}
        assert templates["alpha"].description == "Alpha project"
        assert templates["beta"].description == "Beta user"

    def test_empty_when_no_templates(self, tmp_path, monkeypatch):
        (tmp_path / "empty-project").mkdir(parents=True, exist_ok=True)
        (tmp_path / "empty-home").mkdir(parents=True, exist_ok=True)
        monkeypatch.chdir(tmp_path / "empty-project")
        monkeypatch.setenv("HOME", str(tmp_path / "empty-home"))
        assert list_templates() == []

    def test_scope_mapping(self):
        assert TemplateInfo("a", "d", "Project", Path("x")).scope() == "project"
        assert TemplateInfo("a", "d", "Global", Path("x")).scope() == "user"


# ---------------------------------------------------------------------------
# Execution (run_template)
# ---------------------------------------------------------------------------


class TestRunTemplate:
    def test_same_result_as_cli(self, project_dir, user_dir):
        # The CLI computes: template with $ARGUMENTS replaced by the
        # space-joined arguments. The TUI must produce the identical text.
        result = run_template("alpha", ["hello world"])
        assert result == "# Alpha project\nA: hello world\n"

    def test_no_arguments_replaces_with_empty(self, project_dir, user_dir):
        result = run_template("alpha", [])
        assert result == "# Alpha project\nA: \n"

    def test_multiple_arguments_joined(self, project_dir, user_dir):
        result = run_template("alpha", ["a", "b", "c"])
        assert result == "# Alpha project\nA: a b c\n"

    def test_user_scope_template(self, project_dir, user_dir):
        result = run_template("beta", ["x"])
        assert result == "# Beta user\nB: x\n"

    def test_missing_template_raises(self, project_dir, user_dir):
        with pytest.raises(CommandNotFoundError):
            run_template("nope", ["x"])

    def test_unreadable_template_raises_read_error(self, project_dir, user_dir, monkeypatch):
        monkeypatch.setattr(
            Path, "read_text", lambda self, encoding=None: (_ for _ in ()).throw(OSError("boom"))
        )
        with pytest.raises(TemplateReadError):
            run_template("alpha", ["x"])


# ---------------------------------------------------------------------------
# Project initialization (init_project)
# ---------------------------------------------------------------------------


class TestInitProject:
    def test_creates_structure_and_example(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = actions.init_project()
        assert result.error is None
        assert "Created example template: exemplo.md" in result.created
        assert "Created directory: .promptcraft/commands/" in result.created
        example = tmp_path / ".promptcraft" / "commands" / "exemplo.md"
        assert example.exists()
        assert example.read_text(encoding="utf-8") == EXAMPLE_TEMPLATE

    def test_idempotent_never_overwrites(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        commands = tmp_path / ".promptcraft" / "commands"
        commands.mkdir(parents=True)
        custom = commands / "exemplo.md"
        custom.write_text("MY CUSTOM CONTENT\n", encoding="utf-8")
        other = commands / "other.md"
        other.write_text("# Other\n", encoding="utf-8")

        first = actions.init_project()
        second = actions.init_project()

        assert first.error is None and second.error is None
        # Custom content was preserved on both runs
        assert custom.read_text(encoding="utf-8") == "MY CUSTOM CONTENT\n"
        assert other.read_text(encoding="utf-8") == "# Other\n"
        # Second run reports everything as already existing
        assert "Example template already exists: exemplo.md" in second.existing
        assert not second.created

    def test_permission_error_reports_error(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        def raise_perm(self, *args, **kwargs):
            raise PermissionError("denied")

        monkeypatch.setattr(Path, "mkdir", raise_perm)
        result = actions.init_project()
        assert isinstance(result, InitResult)
        assert result.error is not None
        assert "Permission denied" in result.error

    def test_os_error_reports_error(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        def raise_os(self, *args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(Path, "mkdir", raise_os)
        result = actions.init_project()
        assert result.error is not None
        assert "disk full" in result.error


# ---------------------------------------------------------------------------
# Save / load templates
# ---------------------------------------------------------------------------


class TestSaveTemplate:
    def test_saves_to_project_scope(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        path = save_template("my-command", "project", "# My command\nBody $ARGUMENTS\n")
        assert path == tmp_path / ".promptcraft" / "commands" / "my-command.md"
        assert path.read_text(encoding="utf-8") == "# My command\nBody $ARGUMENTS\n"

    def test_saves_to_user_scope(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        path = save_template("global-cmd", "user", "# Global\n")
        assert path == tmp_path / ".promptcraft" / "commands" / "global-cmd.md"
        assert path.read_text(encoding="utf-8") == "# Global\n"

    def test_strips_trailing_md_extension(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        path = save_template("name.md", "project", "# Name\n")
        assert path.name == "name.md"  # not name.md.md
        assert path.stem == "name"

    def test_discovery_sees_new_template_immediately(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        save_template("fresh", "project", "# Fresh\n")
        names = [t.name for t in list_templates()]
        assert "fresh" in names

    def test_invalid_names_rejected(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        for bad in ["", "   ", "a/b", "a\\b", ".hidden"]:
            with pytest.raises(ValueError):
                save_template(bad, "project", "# X\n")
        # Nothing was written
        assert not (tmp_path / ".promptcraft").exists()

    def test_unknown_scope_rejected(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(ValueError):
            save_template("ok-name", "nope", "# X\n")

    def test_os_error_surfaces(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        def raise_os(self, *args, **kwargs):
            raise OSError("read-only filesystem")

        monkeypatch.setattr(Path, "mkdir", raise_os)
        with pytest.raises(OSError):
            save_template("will-fail", "project", "# X\n")

    def test_load_template_content(self, tmp_path):
        f = tmp_path / "t.md"
        f.write_text("# T\nbody\n", encoding="utf-8")
        assert actions.load_template_content(f) == "# T\nbody\n"

    def test_load_missing_template_raises(self, tmp_path):
        with pytest.raises(OSError):
            actions.load_template_content(tmp_path / "missing.md")


class TestDeleteTemplate:
    def test_deletes_project_template(self, project_dir, user_dir):
        target = project_dir / ".promptcraft" / "commands" / "alpha.md"
        assert target.exists()
        delete_template(target)
        assert not target.exists()
        # Discovery sees the removal immediately.
        assert "alpha" not in [t.name for t in list_templates()]

    def test_deletes_user_template(self, project_dir, user_dir):
        target = user_dir / ".promptcraft" / "commands" / "beta.md"
        delete_template(target)
        assert not target.exists()
        assert "beta" not in [t.name for t in list_templates()]

    def test_missing_file_raises(self, project_dir, user_dir):
        ghost = project_dir / ".promptcraft" / "commands" / "ghost.md"
        with pytest.raises(FileNotFoundError):
            delete_template(ghost)

    def test_outside_scope_rejected(self, tmp_path, project_dir, user_dir):
        outsider = tmp_path / "elsewhere.md"
        outsider.write_text("# Keep me\n", encoding="utf-8")
        with pytest.raises(ValueError, match="outside template directories"):
            delete_template(outsider)
        assert outsider.read_text(encoding="utf-8") == "# Keep me\n"

    def test_directory_itself_rejected(self, project_dir):
        cmd_dir = project_dir / ".promptcraft" / "commands"
        with pytest.raises(ValueError, match="outside template directories"):
            delete_template(cmd_dir)

    def test_subdirectory_rejected(self, project_dir):
        sub_dir = project_dir / ".promptcraft" / "commands" / "subdir"
        sub_dir.mkdir()
        with pytest.raises(ValueError, match="Cannot delete directory"):
            delete_template(sub_dir)


class TestNameValidation:
    def test_valid_names(self):
        assert validate_template_name("my-command") is None
        assert validate_template_name("my_command") is None
        assert validate_template_name("my command") is None
        assert validate_template_name("my-command.md") is None
        assert validate_template_name("  spaced  ") is None

    def test_invalid_names(self):
        assert "required" in validate_template_name("")
        assert "required" in validate_template_name("   ")
        assert "path separators" in validate_template_name("a/b")
        assert "path separators" in validate_template_name("a\\b")
        assert "dot" in validate_template_name(".hidden")
        # ".md" alone normalizes to an empty name
        assert "required" in validate_template_name(".md")

    def test_normalize_name(self):
        assert normalize_name("  foo  ") == "foo"
        assert normalize_name("foo.MD") == "foo"
        assert normalize_name("foo.md.md") == "foo.md"
        assert normalize_name("foo") == "foo"

    def test_template_file_path(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        path = actions.template_file_path("x.md", "project")
        assert path == tmp_path / ".promptcraft" / "commands" / "x.md"
        with pytest.raises(ValueError):
            actions.template_file_path("  ", "project")


# ---------------------------------------------------------------------------
# Clipboard reuse and version
# ---------------------------------------------------------------------------


class TestClipboardAndVersion:
    def test_headless_environment_returns_false(self, monkeypatch):
        monkeypatch.setenv("PROMPTCRAFT_NO_CLIPBOARD", "true")
        assert actions.copy_to_clipboard("anything", "cmd") is False
        assert actions.is_headless_environment() is True

    def test_reuses_cli_copy_helper(self, monkeypatch):
        calls = []

        def fake_copy(text, command_name):
            calls.append((text, command_name))
            return True

        monkeypatch.setattr("promptcraft.main._copy_to_clipboard", fake_copy)
        assert actions.copy_to_clipboard("hello", "cmd") is True
        assert calls == [("hello", "cmd")]

    def test_version_matches_package(self):
        assert actions.get_version() == __version__
