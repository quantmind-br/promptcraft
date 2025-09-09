"""Core functionality for PromptCraft template processing."""

from pathlib import Path
from typing import List, NamedTuple, Dict, Optional, Tuple
import re
import os
import time
from functools import lru_cache

from .exceptions import TemplateError, CommandNotFoundError, TemplateReadError


# Cache for directory modification times and discovery results
_DISCOVERY_CACHE: Dict[str, Tuple[float, List['CommandInfo']]] = {}
_PATH_CACHE: Dict[str, Tuple[float, Optional[Path]]] = {}


class CommandInfo(NamedTuple):
    """Information about a discovered command template."""
    name: str
    path: Path
    source: str  # "Project" or "Global"
    description: str


class TemplateProcessor:
    """Core template processing functionality."""

    def __init__(self) -> None:
        """Initialize the template processor."""
        pass

    def process_template(self, template_content: str) -> str:
        """Process a template and return the result.

        Args:
            template_content: The template content to process

        Returns:
            The processed template result

        Raises:
            TemplateError: If template_content is None or empty
        """
        if template_content is None:
            raise TemplateError("Template content cannot be None")

        if not isinstance(template_content, str):
            raise TemplateError("Template content must be a string")

        if not template_content.strip():
            raise TemplateError("Template content cannot be empty")

        # Placeholder implementation - returns content as-is for now
        return template_content


def find_command_path(command_name: str) -> Path:
    """Find a command template file in the hierarchical search paths with caching.

    Searches for command template files in the following order:
    1. .promptcraft/commands/ in the current working directory
    2. .promptcraft/commands/ in the user's home directory

    Uses caching based on directory modification times to avoid repeated filesystem calls.

    Args:
        command_name: The name of the command to find (without .md extension)

    Returns:
        pathlib.Path object pointing to the found template file

    Raises:
        CommandNotFoundError: If the command template is not found in any search path

    Example:
        >>> path = find_command_path("my-command")
        >>> print(path)  # /path/to/.promptcraft/commands/my-command.md
    """
    if not command_name or not isinstance(command_name, str):
        raise CommandNotFoundError("Command name must be a non-empty string")

    # Check cache first
    cache_key = command_name
    if cache_key in _PATH_CACHE:
        cached_time, cached_result = _PATH_CACHE[cache_key]
        # Cache valid for 5 seconds to balance performance vs freshness
        if time.time() - cached_time < 5.0:
            if cached_result is None:
                # Cached miss
                search_locations = [
                    str(Path.cwd() / ".promptcraft" / "commands"),
                    str(Path.home() / ".promptcraft" / "commands")
                ]
                error_message = (
                    f"Command '{command_name}' not found. "
                    f"Searched in: {', '.join(search_locations)}"
                )
                raise CommandNotFoundError(error_message)
            else:
                # Cached hit
                return cached_result

    # Construct the filename with .md extension
    filename = f"{command_name}.md"

    # Search paths in hierarchical order
    search_paths = [
        Path.cwd() / ".promptcraft" / "commands" / filename,  # Current working directory
        Path.home() / ".promptcraft" / "commands" / filename  # User home directory
    ]

    # Try each search path in order
    for path in search_paths:
        if path.exists() and path.is_file():
            # Cache the successful result
            _PATH_CACHE[cache_key] = (time.time(), path)
            return path

    # Cache the miss to avoid repeated failed lookups
    _PATH_CACHE[cache_key] = (time.time(), None)

    # If we get here, the command was not found in any location
    search_locations = [str(path.parent) for path in search_paths]
    error_message = (
        f"Command '{command_name}' not found. "
        f"Searched in: {', '.join(search_locations)}"
    )
    raise CommandNotFoundError(error_message)


def generate_prompt(template_path: Path, arguments: List[str]) -> str:
    """Generate a prompt from a template file with argument substitution.

    Reads a template file and replaces the $ARGUMENTS placeholder with a
    space-separated string of the provided arguments. All other template
    content is preserved unchanged.

    Args:
        template_path: Path to the template file to process
        arguments: List of arguments to substitute into the template

    Returns:
        str: The processed prompt string with arguments substituted

    Raises:
        TemplateReadError: If the template file cannot be read due to I/O errors,
                          permissions, missing file, or other file system issues

    Example:
        >>> from pathlib import Path
        >>> template_path = Path("my-template.md")
        >>> args = ["arg1", "arg2", "arg3"]
        >>> prompt = generate_prompt(template_path, args)
        >>> print(prompt)  # Template content with $ARGUMENTS replaced by "arg1 arg2 arg3"

        >>> # Handle empty arguments
        >>> empty_prompt = generate_prompt(template_path, [])
        >>> print(empty_prompt)  # Template content with $ARGUMENTS replaced by ""
    """
    try:
        # Read the template file content
        template_content = template_path.read_text(encoding='utf-8')

        # Convert arguments list to space-separated string
        # Handle empty arguments by replacing with empty string
        arguments_string = ' '.join(arguments) if arguments else ''

        # Replace $ARGUMENTS placeholder with the arguments string
        processed_content = template_content.replace('$ARGUMENTS', arguments_string)

        return processed_content

    except FileNotFoundError:
        raise TemplateReadError(
            f"Template file not found: {template_path}",
            error_code="TEMPLATE_FILE_NOT_FOUND"
        )
    except PermissionError:
        raise TemplateReadError(
            f"Permission denied reading template file: {template_path}",
            error_code="TEMPLATE_PERMISSION_DENIED"
        )
    except UnicodeDecodeError as e:
        raise TemplateReadError(
            f"Failed to decode template file {template_path}: {e}",
            error_code="TEMPLATE_ENCODING_ERROR"
        )
    except OSError as e:
        raise TemplateReadError(
            f"I/O error reading template file {template_path}: {e}",
            error_code="TEMPLATE_IO_ERROR"
        )


def process_command(command_name: str, arguments: List[str]) -> str:
    """Process a command by finding its template and generating the final prompt.

    This function integrates template discovery and processing into a complete
    pipeline. It takes a command name and arguments, finds the appropriate
    template file, processes it with the provided arguments, and returns
    the final prompt string ready for use.

    Processing Pipeline:
    1. Uses find_command_path() to locate the command template file
    2. Uses generate_prompt() to process the template with provided arguments
    3. Returns the final processed prompt string

    Args:
        command_name: The name of the command to process (without .md extension)
        arguments: List of arguments to substitute into the template

    Returns:
        str: The final processed prompt string ready for clipboard or display

    Raises:
        CommandNotFoundError: If the command template is not found in any search path.
                             Error message includes command name context for better user experience.
        TemplateReadError: If the template file cannot be read due to I/O errors,
                          permissions, missing file, or other file system issues.
                          Error message includes command name context for better debugging.

    Example:
        >>> # Process a command with arguments
        >>> prompt = process_command("my-command", ["arg1", "arg2", "arg3"])
        >>> print(prompt)  # Final processed prompt with arguments substituted

        >>> # Process a command without arguments
        >>> simple_prompt = process_command("simple-command", [])
        >>> print(simple_prompt)  # Final processed prompt with empty arguments

        >>> # Handle command not found
        >>> try:
        ...     process_command("nonexistent", ["args"])
        ... except CommandNotFoundError as e:
        ...     print(f"Error: {e}")  # Includes command name for context

        >>> # Handle template read errors
        >>> try:
        ...     process_command("broken-permissions", ["args"])
        ... except TemplateReadError as e:
        ...     print(f"Error: {e}")  # Includes command name for context
    """
    try:
        # Step 1: Find the command template path
        template_path = find_command_path(command_name)

        # Step 2: Generate the prompt from the template with arguments
        processed_prompt = generate_prompt(template_path, arguments)

        return processed_prompt

    except CommandNotFoundError as e:
        # Enhance error context with command name for better user experience
        enhanced_message = f"Command '{command_name}' processing failed: {e}"
        raise CommandNotFoundError(enhanced_message) from e

    except TemplateReadError as e:
        # Enhance error context with command name for better debugging
        enhanced_message = f"Command '{command_name}' template processing failed: {e}"
        raise TemplateReadError(enhanced_message, error_code=e.error_code) from e


def _extract_description(file_path: Path) -> str:
    """Extract description from first line of template file with optimized reading.
    
    Args:
        file_path: Path to the template file
        
    Returns:
        First meaningful line as description, with markdown headers cleaned
    """
    try:
        # Read only first 256 bytes to improve performance even more
        # This covers most reasonable first lines while being very fast
        with open(file_path, 'r', encoding='utf-8', buffering=8192) as f:
            # Read a smaller chunk - most descriptions are in first line
            chunk = f.read(256)
            if not chunk:
                return "No description available"
            
            # Get first non-empty line from chunk - optimized for speed
            newline_pos = chunk.find('\n')
            if newline_pos > 0:
                first_line = chunk[:newline_pos].strip()
            else:
                first_line = chunk.strip()
            
            if first_line:
                # Fast markdown header removal using string operations
                if first_line.startswith('#'):
                    # Find where content starts after #'s and optional space
                    start = 0
                    while start < len(first_line) and first_line[start] == '#':
                        start += 1
                    if start < len(first_line) and first_line[start] == ' ':
                        start += 1
                    cleaned = first_line[start:].strip()
                    return cleaned if cleaned else "No description available"
                else:
                    return first_line
        
        return "No description available"
        
    except (OSError, UnicodeDecodeError, PermissionError):
        return "No description available"


def discover_commands() -> List[CommandInfo]:
    """Discover all available command templates with caching for better performance.
    
    Uses caching based on directory modification times to avoid repeated filesystem scans.
    Cache is invalidated when directories are modified.
    
    Returns:
        List of CommandInfo objects with details about each discovered command
    """
    # Search paths in hierarchical order
    search_paths = [
        (Path.cwd() / ".promptcraft" / "commands", "Project"),
        (Path.home() / ".promptcraft" / "commands", "Global")
    ]
    
    # Check if we can use cached results
    cache_key = "discover_commands"
    current_mod_times = []
    
    for search_dir, _ in search_paths:
        if search_dir.exists() and search_dir.is_dir():
            try:
                # Get directory modification time
                mod_time = search_dir.stat().st_mtime
                current_mod_times.append(mod_time)
            except (OSError, PermissionError):
                current_mod_times.append(0)  # Use 0 for inaccessible directories
        else:
            current_mod_times.append(0)  # Use 0 for non-existent directories
    
    # Check cache validity
    cache_mod_time = max(current_mod_times) if current_mod_times else 0
    if cache_key in _DISCOVERY_CACHE:
        cached_time, cached_commands = _DISCOVERY_CACHE[cache_key]
        # Use cached results if directory hasn't been modified and cache is recent (< 10 seconds)
        if cached_time >= cache_mod_time and (time.time() - cached_time) < 10.0:
            return cached_commands
    
    # Perform discovery
    commands = []
    
    for search_dir, source in search_paths:
        if not search_dir.exists() or not search_dir.is_dir():
            continue
            
        try:
            # Use iterdir for better performance than glob for simple patterns
            for item in search_dir.iterdir():
                if item.is_file() and item.suffix == '.md':
                    # Extract command name (remove .md extension)
                    command_name = item.stem
                    
                    # Get description from first line
                    description = _extract_description(item)
                    
                    # Create command info
                    commands.append(CommandInfo(
                        name=command_name,
                        path=item,
                        source=source,
                        description=description
                    ))
                    
        except (OSError, PermissionError):
            # Skip directories we can't read
            continue
    
    # Sort alphabetically by command name (case-insensitive)
    commands.sort(key=lambda cmd: cmd.name.lower())
    
    # Cache the results
    _DISCOVERY_CACHE[cache_key] = (time.time(), commands)
    
    return commands
