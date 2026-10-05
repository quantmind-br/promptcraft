"""Action layer for the PromptCraft TUI.

Every function here reuses the existing CLI logic (template discovery,
template processing, clipboard handling, project initialization) so a
template produces exactly the same result whether it is run from the
command line or from the interactive interface.

These functions are pure (no Textual imports) so they can be unit-tested
without an event loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

from .. import __version__
from ..example_template import EXAMPLE_TEMPLATE
from ..main import CLIPBOARD_OSC52

# Scope identifiers used by the TUI
PROJECT_SCOPE = "project"
USER_SCOPE = "user"

# Mapping between the scope identifier and the source label used by
# core.discover_commands ("Project" / "Global").
SCOPE_LABELS = {PROJECT_SCOPE: "Project", USER_SCOPE: "Global"}
_LABEL_TO_SCOPE = {value: key for key, value in SCOPE_LABELS.items()}


@dataclass
class TemplateInfo:
    """A template as shown in the TUI list."""

    name: str
    description: str
    source: str  # "Project" or "Global" (same labels as the CLI)
    path: Path

    def scope(self) -> str:
        """Scope identifier for this template ("project" or "user")."""
        return _LABEL_TO_SCOPE.get(self.source, PROJECT_SCOPE)


@dataclass
class InitResult:
    """Outcome of an idempotent project initialization."""

    created: List[str] = field(default_factory=list)
    existing: List[str] = field(default_factory=list)
    error: Optional[str] = None


def scope_dir(scope: str) -> Path:
    """Return the ``.promptcraft/commands`` directory for a scope."""
    if scope == USER_SCOPE:
        return Path.home() / ".promptcraft" / "commands"
    return Path.cwd() / ".promptcraft" / "commands"


def list_templates() -> List[TemplateInfo]:
    """Discover available templates the same way the CLI does.

    Reuses :func:`promptcraft.core.discover_commands` (same two search
    locations and same first-line description extraction). When the same
    name exists in both scopes, the project template wins — the same
    precedence the CLI applies when resolving a command by name.
    """
    from ..core import discover_commands

    commands = discover_commands()
    by_name = {}
    for cmd in commands:
        info = TemplateInfo(
            name=cmd.name,
            description=cmd.description,
            source=cmd.source,
            path=cmd.path,
        )
        current = by_name.get(cmd.name)
        if current is None or (
            current.source != "Project" and info.source == "Project"
        ):
            by_name[cmd.name] = info
    return sorted(by_name.values(), key=lambda t: t.name.lower())


def run_template(name: str, arguments: List[str]) -> str:
    """Process a template with the exact pipeline the CLI uses.

    Delegates to :func:`promptcraft.core.process_command` (name lookup
    with project-over-user precedence, then ``$ARGUMENTS`` substitution)
    so the final text is identical to a command-line execution.
    """
    from ..core import process_command

    return process_command(name, arguments)


def copy_to_clipboard(
    text: str, osc52_writer: Optional[Callable[[str], None]] = None
) -> Optional[str]:
    """Copy text to the clipboard, reusing the CLI helper.

    ``osc52_writer`` emits the text as an OSC 52 clipboard write when the
    copy has to go through the terminal (herdr, SSH); the TUI passes
    Textual's ``App.copy_to_clipboard``.

    Returns:
        The route that carried the copy (``main.CLIPBOARD_NATIVE`` or
        ``CLIPBOARD_OSC52``), or None when nothing was copied.
    """
    from ..main import _copy_to_clipboard_route

    return _copy_to_clipboard_route(text, osc52_writer)


def is_headless_environment() -> bool:
    """Report whether the clipboard is expected to be unavailable."""
    from ..main import _is_headless_environment

    return _is_headless_environment()


def get_version() -> str:
    """Return the installed PromptCraft version string."""
    return __version__


def normalize_name(name: str) -> str:
    """Normalize a user-supplied template name into a file stem.

    The CLI convention is that the command name is the ``.md`` file stem
    (a template ``foo.md`` is run as ``promptcraft foo``). A trailing
    ``.md`` typed in the TUI name field is stripped so the saved file
    keeps that convention.
    """
    name = name.strip()
    if name.lower().endswith(".md"):
        name = name[: -len(".md")]
    return name.strip()


def validate_template_name(name: str) -> Optional[str]:
    """Validate a normalized template name.

    Returns an error message, or ``None`` when the name is valid.
    The rules mirror what the CLI can discover and process: the name is
    a plain file stem inside ``.promptcraft/commands/``.
    """
    name = normalize_name(name)
    if not name:
        return "Name is required."
    if "/" in name or "\\" in name:
        return "Name cannot contain path separators ('/' or '\\'). Use a single word or use hyphens."
    if name.startswith("."):
        return "Name cannot start with a dot."
    return None


def init_project() -> InitResult:
    """Idempotently initialize the project structure in the current directory.

    Mirrors the ``--init`` behavior: creates ``.promptcraft/commands/``
    and writes the example template only when it does not exist yet —
    existing templates are never overwritten.
    """
    result = InitResult()
    commands_dir = Path(".promptcraft") / "commands"
    try:
        dir_existed = commands_dir.is_dir()
        commands_dir.mkdir(parents=True, exist_ok=True)
        if dir_existed:
            result.existing.append("Directory already exists: .promptcraft/commands/")
        else:
            result.created.append("Created directory: .promptcraft/commands/")

        example_file = commands_dir / "exemplo.md"
        if not example_file.exists():
            example_file.write_text(EXAMPLE_TEMPLATE, encoding="utf-8")
            result.created.append("Created example template: exemplo.md")
        else:
            result.existing.append("Example template already exists: exemplo.md")
    except PermissionError:
        result.error = "Permission denied: cannot create the project structure. Try running in a directory you can write to."
        return result
    except OSError as e:
        result.error = f"Error creating project structure: {e}"
        return result
    return result


def load_template_content(path: Path) -> str:
    """Read a template file's content (raises OSError/UnicodeDecodeError)."""
    return path.read_text(encoding="utf-8")


def save_template(name: str, scope: str, content: str) -> Path:
    """Save a template file in the chosen scope (project or user).

    The file is written as ``<name>.md`` inside the scope's
    ``.promptcraft/commands/`` directory (created if needed) using the
    same content conventions the CLI uses to discover and process
    templates. Existing files are overwritten — the TUI warns before
    saving when that happens.
    """
    normalized = normalize_name(name)
    error = validate_template_name(normalized)
    if error:
        raise ValueError(error)
    if scope not in (PROJECT_SCOPE, USER_SCOPE):
        raise ValueError(f"Unknown scope: {scope}")

    commands_dir = scope_dir(scope)
    commands_dir.mkdir(parents=True, exist_ok=True)
    path = commands_dir / f"{normalized}.md"
    path.write_text(content, encoding="utf-8")

    # Make sure discovery and path lookups see the change immediately.
    from ..core import invalidate_caches

    invalidate_caches()
    return path


def template_file_path(name: str, scope: str) -> Path:
    """Return the path a template name would have in a scope (no writes)."""
    normalized = normalize_name(name)
    if not normalized:
        raise ValueError("Name is required.")
    return scope_dir(scope) / f"{normalized}.md"


def delete_template(path: Path) -> None:
    """Delete a template file from its scope directory.

    Only files inside one of the two known template directories
    (``.promptcraft/commands/`` in the project or in the user home) can
    be deleted — anything else raises ``ValueError`` instead of
    touching the filesystem.

    Raises:
        ValueError: If the path is outside both template directories.
        FileNotFoundError: If the template file does not exist.
        OSError: If the file cannot be removed (permissions, ...).
    """
    resolved = path.resolve()
    allowed = (scope_dir(PROJECT_SCOPE).resolve(), scope_dir(USER_SCOPE).resolve())
    if not any(
        resolved != base and resolved.is_relative_to(base) for base in allowed
    ):
        raise ValueError(
            f"Refusing to delete outside template directories: {path}"
        )
    if path.is_dir():
        raise ValueError(f"Cannot delete directory: {path}")
    path.unlink()

    # Make sure discovery and path lookups see the change immediately.
    from ..core import invalidate_caches

    invalidate_caches()
