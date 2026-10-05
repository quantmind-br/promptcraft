"""Interactive terminal UI package for PromptCraft."""

from .app import PromptCraftTUI

__all__ = ["PromptCraftTUI", "run_tui"]


def run_tui() -> None:
    """Launch the PromptCraft interactive terminal UI (blocking)."""
    PromptCraftTUI().run()
