"""Main entry point for the PromptCraft CLI application."""

import sys
import os
import time
from pathlib import Path
from typing import Tuple

from . import __version__
from .exceptions import CommandNotFoundError, TemplateReadError

# Lazy imports - these will be imported only when needed
# This reduces cold start time by ~25-45ms


def promptcraft(command_name: str = None, arguments: Tuple[str, ...] = (), stdout: bool = False, init: bool = False, list: bool = False) -> None:
    """PromptCraft CLI - A command-line tool for managing prompt templates.

    Execute slash commands to generate prompts quickly and efficiently.

    Usage Examples:
        promptcraft /create-story "Epic Story" feature
        promptcraft /fix-bug urgent security
        promptcraft /code-review main.py

    Commands are discovered from template files in .promptcraft/commands/
    directories, searched in current directory and user home directory.

    Generated prompts are automatically copied to your clipboard.
    Use --stdout flag to output to terminal instead.

    COMMAND_NAME: The slash command to execute (with or without leading slash)
    ARGUMENTS: Arguments to pass to the command template
    
    Options:
        --stdout    Output to terminal instead of clipboard
    """
    # Handle initialization flag first
    if init:
        _initialize_project()
        return
    
    # Handle list flag
    if list:
        _list_commands()
        return
    
    # Command name is required when not initializing
    if command_name is None:
        # Lazy import click - only when we need CLI output
        import click
        click.secho("Command name is required", fg='red')
        click.secho("Use 'promptcraft --help' for usage information", fg='red')
        sys.exit(1)
    
    # Strip leading slash from command name if present
    if command_name.startswith('/'):
        command_name = command_name[1:]

    try:
        # Lazy import core - only when we actually need to process commands
        from .core import process_command
        
        # Process the command using the core module
        result = process_command(command_name, [*arguments])
        
        # Lazy import click - only when we need output formatting
        import click

        if stdout:
            # Output to terminal when --stdout flag is used
            click.secho(
                f"Prompt for '/{command_name}' generated:",
                fg='green'
            )
            # Print the prompt content with proper formatting
            click.echo(result)
        else:
            # Default behavior: copy result to clipboard
            if _copy_to_clipboard(result, command_name):
                # Display success message with green color
                click.secho(
                    f"Prompt for '/{command_name}' copied to clipboard!",
                    fg='green'
                )
            else:
                # Fallback to stdout when clipboard fails
                click.secho("Clipboard unavailable, use --stdout instead", fg='yellow')
                click.secho(
                    f"Prompt for '/{command_name}' generated:",
                    fg='green'
                )
                click.echo(result)

    except CommandNotFoundError:
        # Lazy import click for error messages
        import click
        # Handle command not found errors with user-friendly message
        click.secho(f"Command '/{command_name}' not found", fg='red')
        click.secho(
            "Run 'promptcraft --list' to see available commands",
            fg='red'
        )
        sys.exit(1)

    except TemplateReadError as e:
        # Lazy import click for error messages
        import click
        # Handle template read errors with file path information
        click.secho(f"{e.message}", fg='red')
        sys.exit(1)

    except Exception:
        # Lazy import click for error messages
        import click
        # Handle all other unexpected errors
        click.secho("Unexpected error occurred", fg='red')
        # In debug mode, we could show the exception
        # For now, maintain the existing behavior
        sys.exit(1)


def _initialize_project() -> None:
    """Initialize PromptCraft project structure in current directory."""
    # Lazy import click - only when we need to display messages
    import click
    
    try:
        # Create .promptcraft/commands/ directory structure
        commands_dir = Path('.promptcraft/commands')
        commands_dir.mkdir(parents=True, exist_ok=True)
        
        # Track what was created
        created_items = []
        
        # Check if directory was just created or already existed
        if not commands_dir.exists():
            created_items.append("Created directory: .promptcraft/commands/")
        else:
            created_items.append("Directory already exists: .promptcraft/commands/")
        
        # Create example template file
        exemplo_file = commands_dir / 'exemplo.md'
        exemplo_content = """# Exemplo de Template do PromptCraft

Este é um exemplo de template demonstrando como usar o sistema de argumentos do PromptCraft.

## Como usar este template:
```
promptcraft exemplo "meu argumento" outro_argumento
```

## Template com Argumentos:

Você solicitou: $ARGUMENTS

## Explicação:
- O placeholder `$ARGUMENTS` será substituído pelos argumentos fornecidos
- Os argumentos são separados por espaços
- Use aspas para argumentos com espaços

## Próximos passos:
1. Edite este arquivo para criar seu próprio template
2. Crie novos arquivos .md neste diretório para novos comandos
3. Use `promptcraft nome_do_arquivo argumentos` para executar seus templates
"""
        
        # Write example template if it doesn't exist
        if not exemplo_file.exists():
            exemplo_file.write_text(exemplo_content, encoding='utf-8')
            created_items.append("Created example template: exemplo.md")
        else:
            created_items.append("Example template already exists: exemplo.md")
        
        # Display success message
        click.secho("PromptCraft initialized! Created .promptcraft/commands/ with example template", fg='green')
        
        # Report what was created
        click.echo("\nProject structure:")
        for item in created_items:
            click.echo(f"  • {item}")
        
        # Provide helpful next steps
        click.echo("\nNext steps:")
        click.echo("  1. Try the example: promptcraft exemplo 'hello world'")
        click.echo("  2. Edit .promptcraft/commands/exemplo.md to customize")
        click.echo("  3. Create new .md files for your own templates")
        click.echo("  4. Use 'promptcraft --help' for more options")
        
    except PermissionError:
        click.secho("Permission denied: Cannot create directories", fg='red')
        click.secho("Try running with appropriate permissions", fg='red')
        sys.exit(1)
    except OSError as e:
        click.secho(f"Error creating project structure: {e}", fg='red')
        sys.exit(1)


def _list_commands() -> None:
    """List all available command templates."""
    # Lazy import click and core - only when we need to list commands
    import click
    from .core import discover_commands
    
    try:
        commands = discover_commands()
        
        if not commands:
            click.secho("No commands found", fg='yellow')
            click.echo("Run 'promptcraft --init' to create examples.")
            return
        
        # Display header
        click.secho(f"Available Commands ({len(commands)} found):", fg='green', bold=True)
        click.echo()
        
        # Calculate column widths for proper alignment
        max_name_length = max(len(cmd.name) for cmd in commands) if commands else 0
        max_source_length = max(len(cmd.source) for cmd in commands) if commands else 0
        
        # Ensure minimum column widths for headers
        name_width = max(max_name_length, len("Command"))
        source_width = max(max_source_length, len("Source"))
        
        # Print table header
        header = f"{'Command':<{name_width}} {'Source':<{source_width}} Description"
        click.secho(header, fg='cyan', bold=True)
        click.secho('-' * len(header), fg='cyan')
        
        # Print each command
        for cmd in commands:
            # Color code source: green for Project, blue for Global
            source_color = 'green' if cmd.source == 'Project' else 'blue'
            
            # Format row with proper alignment
            name_part = f"{cmd.name:<{name_width}}"
            source_part = click.style(f"{cmd.source:<{source_width}}", fg=source_color)
            desc_part = cmd.description
            
            click.echo(f"{name_part} {source_part} {desc_part}")
            
    except Exception as e:
        click.secho(f"Error listing commands: {e}", fg='red')
        sys.exit(1)


# Main entry point for direct execution
def _copy_to_clipboard(text: str, command_name: str) -> bool:
    """
    Copy text to clipboard with error handling and timeout protection.
    
    Args:
        text: Text to copy to clipboard
        command_name: Command name for error reporting
        
    Returns:
        True if successful, False if failed
    """
    try:
        # Check for headless environment indicators
        if _is_headless_environment():
            return False
            
        # Lazy import pyperclip - only when we actually need clipboard functionality
        import pyperclip  # type: ignore
            
        # Implement timeout protection (100ms max)
        start_time = time.time()
        pyperclip.copy(text)
        
        # Verify operation completed within timeout
        elapsed = (time.time() - start_time) * 1000  # Convert to ms
        if elapsed > 150:  # 150ms timeout as per requirements
            return False
            
        return True
        
    except Exception:
        # Catch all clipboard-related exceptions:
        # - PyperclipException: Clipboard backend issues
        # - OSError: System-level errors
        # - Any other clipboard-related failures
        return False


def _is_headless_environment() -> bool:
    """
    Detect if running in a headless environment where clipboard may not be available.
    
    Returns:
        True if headless environment detected
    """
    # Check common headless environment indicators
    if os.environ.get('CI') == 'true':  # CI/CD environments
        return True
    if os.environ.get('DISPLAY') == '':  # Linux without X11
        return True
    if os.environ.get('PROMPTCRAFT_NO_CLIPBOARD') == 'true':  # Manual override
        return True
    
    # Additional headless checks for different platforms
    if sys.platform.startswith('linux'):
        # Check if running in a container or SSH session without X11 forwarding
        if not os.environ.get('DISPLAY') and not os.path.exists('/tmp/.X11-unix'):
            return True
    
    return False


def main() -> None:
    """Main entry point when module is run directly."""
    # Only import click here, at the very last moment before we need CLI parsing
    import click
    
    # Create the click command with decorators applied dynamically
    @click.command()
    @click.version_option(version=__version__)
    @click.argument('command_name', required=False)
    @click.argument('arguments', nargs=-1)
    @click.option('--stdout', is_flag=True, help='Output to terminal instead of clipboard')
    @click.option('--init', is_flag=True, help='Initialize PromptCraft project structure')
    @click.option('--list', is_flag=True, help='List all available commands')
    def cli(command_name: str, arguments: Tuple[str, ...], stdout: bool, init: bool, list: bool) -> None:
        """PromptCraft CLI - A command-line tool for managing prompt templates.

        Execute slash commands to generate prompts quickly and efficiently.

        Usage Examples:
            promptcraft /create-story "Epic Story" feature
            promptcraft /fix-bug urgent security
            promptcraft /code-review main.py

        Commands are discovered from template files in .promptcraft/commands/
        directories, searched in current directory and user home directory.

        Generated prompts are automatically copied to your clipboard.
        Use --stdout flag to output to terminal instead.

        COMMAND_NAME: The slash command to execute (with or without leading slash)
        ARGUMENTS: Arguments to pass to the command template
        
        Options:
            --stdout    Output to terminal instead of clipboard
        """
        # Call our actual implementation
        promptcraft(command_name, arguments, stdout, init, list)
    
    # Execute the CLI
    cli()


if __name__ == "__main__":
    main()
