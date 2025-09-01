"""Main entry point for the PromptCraft CLI application."""

import sys
import click
import pyperclip  # type: ignore
from typing import Tuple

from . import __version__
from .core import process_command
from .exceptions import CommandNotFoundError, TemplateReadError


@click.command()
@click.version_option(version=__version__)
@click.argument('command_name')
@click.argument('arguments', nargs=-1)
def promptcraft(command_name: str, arguments: Tuple[str, ...]) -> None:
    """PromptCraft CLI - A command-line tool for managing prompt templates.

    Execute slash commands to generate prompts quickly and efficiently.

    Usage Examples:
        promptcraft /create-story "Epic Story" feature
        promptcraft /fix-bug urgent security
        promptcraft /code-review main.py

    Commands are discovered from template files in .promptcraft/commands/
    directories, searched in current directory and user home directory.

    Generated prompts are automatically copied to your clipboard.

    COMMAND_NAME: The slash command to execute (with or without leading slash)
    ARGUMENTS: Arguments to pass to the command template
    """
    # Strip leading slash from command name if present
    if command_name.startswith('/'):
        command_name = command_name[1:]

    try:
        # Process the command using the core module
        result = process_command(command_name, list(arguments))

        # Copy result to clipboard
        pyperclip.copy(result)

        # Display success message with green color
        click.secho(
            f"✅ Prompt for '/{command_name}' copied to clipboard!",
            fg='green'
        )

    except CommandNotFoundError:
        # Handle command not found errors with user-friendly message
        click.secho(f"❌ Command '/{command_name}' not found", fg='red')
        click.secho(
            "Run 'promptcraft --list' to see available commands",
            fg='red'
        )
        sys.exit(1)

    except TemplateReadError as e:
        # Handle template read errors with file path information
        click.secho(f"❌ {e.message}", fg='red')
        sys.exit(1)

    except Exception:
        # Handle all other unexpected errors
        click.secho("❌ Unexpected error occurred", fg='red')
        sys.exit(1)


# Main entry point for direct execution
def main() -> None:
    """Main entry point when module is run directly."""
    promptcraft()


if __name__ == "__main__":
    main()
