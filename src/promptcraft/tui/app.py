"""Interactive terminal UI for PromptCraft (built on Textual).

Screens:
  * ``HomeScreen`` — navigable list of templates (project and user
    scopes, project wins on name conflicts), with actions to run,
    create, edit, delete, initialize, show the version, and show help.
  * ``RunScreen`` — form to type the template's arguments; the result
    is copied to the clipboard (default) or shown on screen.
  * ``ResultScreen`` — read-only view of a generated prompt with a
    "copy to clipboard" action and clear success/failure feedback.
  * ``TemplateScreen`` — create or edit a ``.md`` template, saved in
    the scope chosen by the user (project or user). Editing to another
    name or scope moves the template there (the original file is
    removed), so a project template can become a user template.
  * ``InitResultScreen`` / ``VersionScreen`` / ``HelpScreen`` —
    feedback for project initialization, the installed version, and
    the full keyboard shortcut reference.

All shortcuts are always visible in the footer of the active screen;
press ``?`` for the full reference.
"""

from __future__ import annotations

from typing import Optional

from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    OptionList,
    Rule,
    Select,
    Static,
    TextArea,
)
from textual.content import Content
from textual.widgets.option_list import Option

from ..exceptions import CommandNotFoundError, TemplateReadError
from . import actions
from .actions import InitResult, TemplateInfo

HELP_TEXT = """\
PromptCraft TUI — keyboard shortcuts
────────────────────────────────────
Home (template list)
  Up / Down        Move through templates
  Enter / r        Run the selected template
  n                Create a new template
  e                Edit the selected template
  d                Delete the selected template (press twice to confirm)
  i                Initialize project structure (.promptcraft)
  v                Show the installed version
  f                Refresh the template list
  ?                Show this help
  q / Esc          Quit

Run template
  Type             Arguments for the $ARGUMENTS placeholder
  Enter / s        Run and copy the result to the clipboard
  d                Run and show the result on screen
  Esc / q          Back (no copy)

Result
  c                Copy the result to the clipboard
  Esc / q          Back

New / edit template
  Ctrl+S / s       Save the template (project or user scope)
                   (Ctrl+S works from any field; s only outside text fields)
                   Editing to another name/scope moves the template there
                   (the original file is removed).
  Ctrl+D           Delete the template being edited (press twice to confirm)
  Esc / q          Back (discard changes)

Init / version / help
  Esc / q          Close
"""


class HomeScreen(Screen):
    """Template list with the main TUI actions."""

    BINDINGS = [
        Binding("r", "run_selected", "Run"),
        Binding("enter", "run_selected", "Run", show=False),
        Binding("n", "new_template", "New"),
        Binding("e", "edit_selected", "Edit"),
        Binding("d", "delete_selected", "Delete"),
        Binding("delete", "delete_selected", "Delete", show=False),
        Binding("i", "initialize", "Init"),
        Binding("v", "version", "Version"),
        Binding("f", "refresh", "Refresh"),
        Binding("?", "help", "Help"),
        Binding("q", "quit", "Quit", priority=True),
        Binding("escape", "cancel_or_quit", "Quit", show=False, priority=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.templates: dict[str, TemplateInfo] = {}
        self.highlighted: Optional[TemplateInfo] = None
        self._confirmed_delete: Optional[str] = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("", id="source-hint")
        yield OptionList(id="templates")
        yield Static("No template selected.", id="details")
        yield Static("", id="status")
        yield Footer()

    def on_mount(self) -> None:
        self.populate_list()
        self.query_one("#templates", OptionList).focus()

    def on_screen_resume(self) -> None:
        """Refresh the list when returning from another screen (e.g. after
        saving a template or initializing the project)."""
        previous = self.highlighted.name if self.highlighted else None
        self.populate_list(keep_highlight=previous)

    def populate_list(self, keep_highlight: Optional[str] = None) -> None:
        """(Re)load the template list from the existing discovery logic.

        When keep_highlight names a template that still exists, its row
        stays highlighted (used when the list refreshes under the user).
        """
        from ..core import invalidate_caches

        invalidate_caches()
        option_list = self.query_one("#templates", OptionList)
        option_list.clear_options()
        self.templates = {}
        new_options = []
        for template in actions.list_templates():
            self.templates[template.name] = template
            new_options.append(
                Option(
                    Content(
                        f"{template.name}  ·  {template.description}  [{template.source}]"
                    ),
                    id=template.name,
                )
            )
        option_list.add_options(new_options)
        if keep_highlight in self.templates:
            option_list.highlighted = option_list.get_option_index(keep_highlight)
        hint = self.query_one("#source-hint", Static)
        if self.templates:
            hint.update(
                f"{len(self.templates)} template(s)  ·  sources: "
                ".promptcraft/commands (project) and ~/.promptcraft/commands (user)"
            )
            self.query_one("#details", Static).update(
                "No template selected. Use Up/Down, then Enter to run."
            )
        else:
            hint.update("No templates found.")
            self.query_one("#details", Static).update(
                "Press n to create a template, or i to initialize the project structure."
            )
        self.highlighted = None
        self._confirmed_delete = None
        option_list.focus()

    def on_option_list_option_highlighted(
        self, event: OptionList.OptionHighlighted
    ) -> None:
        if event.option is None:
            return
        template = self.templates.get(event.option.id)
        if template is None:
            return
        if self._confirmed_delete is not None and self._confirmed_delete != str(template.path):
            self._confirmed_delete = None
            self.query_one("#status", Static).update("")
        self.highlighted = template
        self.query_one(
            "#details", Static
        ).update(Content(f"/{template.name}  ·  [{template.source}]  ·  {template.path}"))

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option is None:
            return
        template = self.templates.get(event.option.id)
        if template is None:
            return
        self.highlighted = template
        self.action_run_selected(template)

    def _selected_template(self) -> Optional[TemplateInfo]:
        if self.highlighted is not None:
            return self.highlighted
        option_list = self.query_one("#templates", OptionList)
        option = option_list.highlighted_option
        if option is None:
            return None
        return self.templates.get(option.id)

    def action_run_selected(self, template: Optional[TemplateInfo] = None) -> None:
        template = template or self._selected_template()
        if template is None:
            self.notify(
                "Select a template first (Up/Down, then Enter).", severity="warning"
            )
            return
        self.app.push_screen(RunScreen(template))

    def action_new_template(self) -> None:
        self.app.push_screen(TemplateScreen(mode="create"))

    def action_edit_selected(self) -> None:
        template = self._selected_template()
        if template is None:
            self.notify(
                "Select the template to edit first (Up/Down, then e).",
                severity="warning",
            )
            return
        self.app.push_screen(TemplateScreen(mode="edit", template=template))

    def action_delete_selected(self) -> None:
        template = self._selected_template()
        if template is None:
            self.notify(
                "Select the template to delete first (Up/Down, then d).",
                severity="warning",
            )
            return
        key = str(template.path)
        if key != self._confirmed_delete:
            self._confirmed_delete = key
            message = (
                f"⚠ Delete '/{template.name}' [{template.source}] "
                f"({template.path})? Press d again to confirm."
            )
            self.query_one("#status", Static).update(Content(message))
            self.notify(message, severity="warning", timeout=8, markup=False)
            return
        self._confirmed_delete = None
        try:
            actions.delete_template(template.path)
        except FileNotFoundError:
            self.query_one("#status", Static).update(
                Content(f"⚠ /{template.name} was already deleted. List refreshed.")
            )
            self.notify(
                f"/{template.name} was already deleted.",
                severity="warning",
                markup=False,
            )
            self.populate_list()
            return
        except (OSError, ValueError) as e:
            self.query_one("#status", Static).update(Content(f"✗ Delete failed: {e}"))
            self.notify(f"Delete failed: {e}", severity="error", timeout=8, markup=False)
            return
        self.query_one("#status", Static).update(
            Content(f"✓ Deleted /{template.name} [{template.source}].")
        )
        self.notify(f"Deleted /{template.name}", severity="information", markup=False)
        self.populate_list()

    def action_initialize(self) -> None:
        result = actions.init_project()
        if result.error:
            self.notify(result.error, severity="error", timeout=10, markup=False)
            self.query_one("#status", Static).update(Content(f"✗ {result.error}"))
            return
        self.query_one("#status", Static).update(
            "✓ Project structure ready (see details)."
        )
        self.app.push_screen(InitResultScreen(result))

    def action_version(self) -> None:
        self.app.push_screen(VersionScreen())

    def action_help(self) -> None:
        self.app.push_screen(HelpScreen())

    def action_refresh(self) -> None:
        self.populate_list()
        self.notify("Template list refreshed.", severity="information")

    def action_quit(self) -> None:
        self.app.exit()

    def action_cancel_or_quit(self) -> None:
        if self._confirmed_delete is not None:
            self._confirmed_delete = None
            self.query_one("#status", Static).update(Content("Delete cancelled."))
            return
        self.action_quit()


class RunScreen(Screen):
    """Fill a template's arguments and run it (clipboard or on-screen)."""

    BINDINGS = [
        Binding("s", "copy", "Copy to clipboard"),
        Binding("enter", "copy", "Copy to clipboard", show=False),
        Binding("d", "display", "Show on screen"),
        Binding("escape", "back", "Back", priority=True),
        Binding("q", "back", "Back", show=False),
    ]

    def __init__(self, template: TemplateInfo) -> None:
        super().__init__()
        self.template = template
        self.result: Optional[str] = None
        self.copied_result: Optional[str] = None

    def compose(self) -> ComposeResult:
        yield Static(
            Content(
                f"Run: /{self.template.name}  ·  [{self.template.source}]  ·  "
                f"{self.template.description}"
            ),
            id="run-title",
        )
        yield Input(
            placeholder=(
                f"Arguments for /{self.template.name} (space-separated, leave empty if none)"
            ),
            id="args",
        )
        yield Static(
            "The $ARGUMENTS placeholder in the template is replaced by the "
            "arguments you type here. Press Enter to run (copies to the "
            "clipboard by default); Tab to the action buttons for the other "
            "option.",
            id="run-hint",
        )
        yield Button("Run → copy to clipboard", id="btn-copy", variant="success")
        yield Button("Run → show on screen", id="btn-show", variant="warning")
        yield Static("", id="status")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#args", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Enter in the arguments field runs the template (copies to clipboard)."""
        self.action_copy()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """The visible action buttons run the template in the chosen mode."""
        if event.button.id == "btn-copy":
            self.action_copy()
        elif event.button.id == "btn-show":
            self.action_display()

    def _set_status(self, message: str) -> None:
        self.query_one("#status", Static).update(Content(str(message)))

    def _run(self) -> Optional[str]:
        args_input = self.query_one("#args", Input)
        raw = args_input.value.strip()
        arguments = [raw] if raw else []
        try:
            self.result = actions.run_template(self.template.name, arguments)
            return self.result
        except (CommandNotFoundError, TemplateReadError) as e:
            self._set_status(f"✗ {e}")
            self.notify(str(e), severity="error", timeout=8, markup=False)
            return None
        except Exception as e:  # unexpected
            self._set_status(f"✗ Unexpected error: {e}")
            self.notify(f"Unexpected error: {e}", severity="error", timeout=8, markup=False)
            return None

    def action_copy(self) -> None:
        # Move focus out of the arguments field so the on-screen shortcuts
        # (d = show on screen, q = back) work right after the run attempt.
        self.query_one("#args", Input).blur()
        result = self._run()
        if result is None:
            return
        if actions.copy_to_clipboard(result, self.template.name):
            self.copied_result = result
            self._set_status(
                f"✓ Copied to clipboard ({len(result)} chars). "
                "Press d to view it on screen, Esc to go back.",
            )
            self.notify(
                f"/{self.template.name} copied to clipboard",
                severity="information",
                markup=False,
            )
        else:
            self._set_status(
                "✗ Could not copy to the clipboard. Press d to view the text on "
                "screen (CLI equivalent: use --stdout)."
            )
            self.notify("Clipboard copy failed", severity="error", timeout=8)

    def action_display(self) -> None:
        self.query_one("#args", Input).blur()  # moving off the Input leaves no confusing caret
        # Always run fresh: the arguments may have changed since the last
        # run, and a previous failure must not mask the new outcome.
        result = self._run()
        if result is None:
            return
        copied = result == self.copied_result
        self.app.push_screen(ResultScreen(self.template.name, result, copied=copied))

    def action_back(self) -> None:
        self.app.pop_screen()


class ResultScreen(Screen):
    """Show a generated prompt read-only, with a copy-to-clipboard action."""

    BINDINGS = [
        Binding("c", "copy", "Copy to clipboard"),
        Binding("escape", "back", "Back", show=False, priority=True),
        Binding("q", "back", "Back", priority=True),
    ]

    def __init__(self, name: str, content: str, copied: bool = False) -> None:
        super().__init__()
        self.template_name = name
        self.result_content = content
        self.copied = copied

    def compose(self) -> ComposeResult:
        yield Static(
            Content(
                f"Result for /{self.template_name}  ·  {len(self.result_content)} chars"
            ),
            id="result-title",
        )
        yield TextArea(classes="result-text", read_only=True)
        yield Static("", id="status")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(".result-text", TextArea).text = self.result_content
        if self.copied:
            self.query_one("#status", Static).update(
                Content("✓ Already copied to the clipboard. Press c to copy again.")
            )
        else:
            self.query_one("#status", Static).update(
                Content("Clipboard was not used for this result. Press c to copy it.")
            )

    def action_copy(self) -> None:
        status = self.query_one("#status", Static)
        if actions.copy_to_clipboard(self.result_content, self.template_name):
            status.update(Content(f"✓ Copied to clipboard ({len(self.result_content)} chars)."))
            self.notify(
                f"/{self.template_name} copied to clipboard",
                severity="information",
                markup=False,
            )
        else:
            status.update(
                Content(
                    "✗ Could not copy to the clipboard. The text is shown here — "
                    "select it with your terminal, or use --stdout on the CLI."
                )
            )
            self.notify("Clipboard copy failed", severity="error", timeout=8)

    def action_back(self) -> None:
        self.app.pop_screen()


class TemplateScreen(Screen):
    """Create or edit a template, saved in the user-chosen scope."""

    BINDINGS = [
        Binding("s", "save", "Save", show=False),
        Binding("ctrl+s", "save", "Save"),
        Binding("ctrl+d", "delete", "Delete"),
        Binding("escape", "back", "Back (discard)"),
        Binding("q", "back", "Back (discard)", show=False),
    ]

    SCOPE_OPTIONS = [
        ("Project — .promptcraft/commands (this project)", actions.PROJECT_SCOPE),
        ("User — ~/.promptcraft/commands (all projects)", actions.USER_SCOPE),
    ]

    def __init__(self, mode: str, template: Optional[TemplateInfo] = None) -> None:
        super().__init__()
        self.mode = mode  # "create" or "edit"
        self.template = template
        self._confirmed_target: Optional[str] = None
        self._confirmed_delete: Optional[str] = None

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == "delete":
            return self.mode == "edit" and self.template is not None
        return True

    def compose(self) -> ComposeResult:
        if self.mode == "edit" and self.template is not None:
            title = (
                f"Editing template: /{self.template.name}  ·  ",
                f"[{self.template.source}]",
            )
        else:
            title = "New template"
        title_text = "".join(title) if isinstance(title, tuple) else title
        yield Static(Content(title_text), id="tpl-title")
        yield Input(value=self._default_name(), placeholder="my-command", id="name")
        yield Select[
            str
        ](options=self.SCOPE_OPTIONS, value=self._default_scope(), id="scope", allow_blank=False)
        yield Static(
            "The first line of the content is shown as the description in the "
            "list. Use $ARGUMENTS where the typed arguments go. "
            "Save with Ctrl+S (or Enter when the name field has focus).",
            id="tpl-hint",
        )
        yield TextArea(classes="content-text", id="content")
        yield Static("", id="status")
        if self.mode == "edit" and self.template is not None:
            yield Button("Delete template", id="btn-delete", variant="error")
        yield Footer()

    def _default_name(self) -> str:
        return self.template.name if self.template else ""

    def _default_scope(self) -> str:
        if self.template is not None:
            return self.template.scope()
        # Create: default to the project scope when a project structure
        # exists in the current directory, otherwise to the user scope.
        if actions.scope_dir(actions.PROJECT_SCOPE).is_dir():
            return actions.PROJECT_SCOPE
        return actions.USER_SCOPE

    def on_mount(self) -> None:
        self.query_one("#name", Input).focus()
        if self.mode == "edit" and self.template is not None:
            try:
                self.query_one("#content", TextArea).text = (
                    actions.load_template_content(self.template.path)
                )
            except (OSError, UnicodeDecodeError) as e:
                self.notify(
                    f"Could not read {self.template.path}: {e}",
                    severity="error",
                    timeout=8,
                    markup=False,
                )
                self.app.pop_screen()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Enter in the name field saves the template."""
        if event.control.id == "name":
            self.action_save()

    def on_key(self, event: events.Key) -> None:
        if event.key == "ctrl+d":
            event.prevent_default()
            event.stop()
            self.action_delete()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-delete":
            self.action_delete()

    def action_back(self) -> None:
        if self._confirmed_delete is not None:
            self._confirmed_delete = None
            self._set_status("Delete cancelled.")
            return
        self.app.pop_screen()

    def _set_status(self, message: str) -> None:
        self.query_one("#status", Static).update(Content(str(message)))

    def action_delete(self) -> None:
        if self.mode != "edit" or self.template is None:
            self._set_status("✗ Cannot delete an unsaved template.")
            self.notify("Cannot delete an unsaved template.", severity="warning")
            return

        key = str(self.template.path)
        if key != self._confirmed_delete:
            self._confirmed_delete = key
            message = (
                f"⚠ Delete '/{self.template.name}' [{self.template.source}]? "
                "Press Ctrl+D again to confirm."
            )
            self._set_status(message)
            self.notify(message, severity="warning", timeout=8, markup=False)
            return

        self._confirmed_delete = None
        try:
            actions.delete_template(self.template.path)
        except FileNotFoundError:
            self.notify(
                f"/{self.template.name} was already deleted.",
                severity="warning",
                markup=False,
            )
            self.app.pop_screen()
            return
        except (OSError, ValueError) as e:
            self._set_status(f"✗ Delete failed: {e}")
            self.notify(f"Delete failed: {e}", severity="error", timeout=8, markup=False)
            return

        self.notify(
            f"Deleted /{self.template.name} [{self.template.source}]",
            severity="information",
            markup=False,
        )
        self.app.pop_screen()

    def action_save(self) -> None:
        self._confirmed_delete = None
        name_raw = self.query_one("#name", Input).value
        scope_value = self.query_one("#scope", Select).value
        scope = scope_value if isinstance(scope_value, str) else actions.PROJECT_SCOPE

        content = self.query_one("#content", TextArea).text

        error = actions.validate_template_name(name_raw)
        if error:
            self._set_status(f"✗ {error}")
            self.notify(error, severity="error", timeout=8)
            return
        if not content.strip():
            self._set_status(
                "✗ Content is required (the first line becomes the description)."
            )
            self.notify("Content is required.", severity="error", timeout=8)
            return

        name = actions.normalize_name(name_raw)
        target = actions.template_file_path(name, scope)
        # Editing to another name or scope moves the template there: the
        # original file is removed once the new one is saved, so a project
        # template can become a user template (and vice versa).
        is_move = (
            self.mode == "edit"
            and self.template is not None
            and target.resolve() != self.template.path.resolve()
        )
        if target.exists():
            is_editing_same_file = (
                self.mode == "edit" and self.template is not None and not is_move
            )
            if not is_editing_same_file and str(target) != self._confirmed_target:
                self._confirmed_target = str(target)
                scope_label = actions.SCOPE_LABELS.get(scope, scope)
                if self.mode == "create":
                    message = (
                        f"⚠ Template '{name}' already exists in the {scope_label} "
                        "scope. Press Ctrl+S again to overwrite it."
                    )
                else:
                    origin = (
                        f"'{self.template.name}' [{self.template.source}]"
                        if self.template is not None
                        else "being edited"
                    )
                    message = (
                        f"⚠ Template '{name}' already exists in the {scope_label} "
                        "scope and will be overwritten (the original "
                        f"{origin} will be removed — this is a move). "
                        "Press Ctrl+S again to confirm."
                    )
                self._set_status(message)
                self.notify(message, severity="warning", timeout=8, markup=False)
                return

        try:
            path = actions.save_template(name, scope, content)
        except (ValueError, PermissionError, OSError) as e:
            self._set_status(f"✗ Save failed: {e}")
            self.notify(f"Save failed: {e}", severity="error", timeout=8, markup=False)
            return

        scope_label = actions.SCOPE_LABELS.get(scope, scope)
        if is_move:
            assert self.template is not None  # guaranteed by is_move
            original = self.template.path
            try:
                if original.resolve() != path.resolve() and original.exists():
                    actions.delete_template(original)
            except OSError as e:
                self.notify(
                    f"Saved {path.name} to {scope_label} scope, but could not "
                    f"remove the original {original}: {e}",
                    severity="warning",
                    timeout=8,
                    markup=False,
                )
                self.app.pop_screen()
                return
            self._set_status(f"✓ Moved: {original} → {path}  ({scope_label} scope)")
            self.notify(
                f"Moved {original.name} from {self.template.source} to "
                f"{scope_label} scope as {path.name}",
                severity="information",
                markup=False,
            )
            self.app.pop_screen()
            return

        self._set_status(f"✓ Saved: {path}  ({scope_label} scope)")
        self.notify(
            f"Saved {path.name} to {scope_label} scope",
            severity="information",
            markup=False,
        )
        self.app.pop_screen()


class InitResultScreen(ModalScreen):
    """Show the outcome of an idempotent project initialization."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close", show=False),
        Binding("enter", "dismiss", "Close", show=False),
    ]

    def __init__(self, result: InitResult) -> None:
        super().__init__()
        self.result = result

    def compose(self) -> ComposeResult:
        lines = [
            "Initialize project structure (.promptcraft) — done, existing templates were not touched.",
            "",
        ]
        lines.extend(f"  • {message}" for message in self.result.created)
        lines.extend(f"  • {message}" for message in self.result.existing)
        yield Static("\n".join(lines), id="init-summary")
        yield Static("Esc to close", classes="modal-panel-hint")

    def on_mount(self) -> None:
        self.notify("Project structure ready.", severity="information")


class VersionScreen(ModalScreen):
    """Show the installed PromptCraft version."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close", show=False),
        Binding("enter", "dismiss", "Close", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Static("Installed version", id="version-title")
        yield Rule()
        yield Static(f"PromptCraft v{actions.get_version()}", id="version-value")
        yield Static("Esc to close", classes="modal-panel-hint")


class HelpScreen(ModalScreen):
    """Show the full keyboard shortcut reference."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close", show=False),
        Binding("?", "dismiss", "Close", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Static("Keyboard shortcuts", id="help-title")
        yield Rule()
        yield Static(HELP_TEXT, id="help-text")
        yield Static("Esc to close", classes="modal-panel-hint")


class PromptCraftTUI(App):
    """The PromptCraft interactive terminal interface."""

    TITLE = "PromptCraft"
    SUB_TITLE = f"v{actions.get_version()}"

    def get_default_screen(self) -> Screen:
        return HomeScreen()
    CSS = """
    #templates {
        height: 1fr;
        border: solid $background 35%;
    }
    #details {
        height: auto;
        margin: 1 0 0 0;
        text-style: dim;
    }
    #status {
        height: auto;
        margin: 1 0 0 0;
    }
    .result-text {
        height: 1fr;
        border: solid $background 35%;
    }
    .content-text {
        height: 1fr;
        border: solid $background 35%;
    }
    .modal-panel-hint {
        margin-top: 1;
        text-style: dim;
    }
    #init-summary, #version-value, #help-text {
        width: 100%;
        background: $surface;
        border: heavy $primary;
        padding: 1 2;
    }
    #btn-delete {
        margin: 1 0 0 0;
    }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=False, priority=True),
    ]
