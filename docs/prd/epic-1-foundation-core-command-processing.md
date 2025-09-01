# Epic 1: Foundation & Core Command Processing

**Epic Goal:** Establish the foundational Python project structure and implement the core engine that discovers command templates and processes them into generated prompts, providing the essential functionality that powers all user interactions.

### Story 1.1: Project Structure and Development Environment

As a developer,
I want a properly structured Python project with dependencies and development environment,
so that I can develop and test the PromptCraft CLI tool effectively.

#### Acceptance Criteria
1. Project follows modern Python packaging structure with `src/promptcraft/` layout
2. `pyproject.toml` configured with project metadata, dependencies (click, pyperclip), and development dependencies (pytest)
3. `.gitignore` configured for Python projects excluding `__pycache__`, `.pytest_cache`, `dist/`, etc.
4. `README.md` contains basic project description and development setup instructions
5. Virtual environment can be created and activated with all dependencies installed
6. Basic project structure includes: `src/promptcraft/__init__.py`, `src/promptcraft/main.py`, `src/promptcraft/core.py`, `src/promptcraft/exceptions.py`

### Story 1.2: Custom Exception Classes

As a developer,
I want well-defined custom exceptions for expected error conditions,
so that the system can handle errors gracefully with appropriate user messaging.

#### Acceptance Criteria
1. `CommandNotFoundError` exception class defined in `src/promptcraft/exceptions.py`
2. `TemplateReadError` exception class defined for file reading issues
3. Both exceptions inherit from appropriate base exception classes
4. Exception classes include helpful docstrings explaining when they should be used
5. Exception classes can be imported and raised properly in other modules

### Story 1.3: Command Template Discovery

As a developer,
I want the system to find command template files in the correct hierarchical order,
so that project-specific commands can override global commands.

#### Acceptance Criteria
1. `find_command_path()` function searches `.promptcraft/commands/` in current working directory first
2. If not found locally, searches `.promptcraft/commands/` in user home directory
3. Function returns pathlib.Path object for the found template file
4. Function raises `CommandNotFoundError` if command template not found in either location
5. Function handles edge cases like missing directories gracefully
6. Function accepts command name parameter and constructs correct `.md` filename

### Story 1.4: Template Processing and Argument Substitution

As a developer,
I want template files to be processed with argument substitution,
so that dynamic prompts can be generated from static templates.

#### Acceptance Criteria
1. `generate_prompt()` function reads template file content from provided path
2. Function replaces `$ARGUMENTS` placeholder with space-separated argument string
3. Function handles empty arguments list gracefully (replaces with empty string)
4. Function raises `TemplateReadError` for file reading errors with helpful error message
5. Function returns processed prompt string ready for use
6. Function preserves all other template content unchanged (markdown formatting, etc.)

### Story 1.5: Integrated Command Processing Pipeline

As a developer,
I want a complete pipeline that takes command name and arguments and returns a processed prompt,
so that all core functionality is connected and testable.

#### Acceptance Criteria
1. `process_command()` function integrates template discovery and processing
2. Function takes command name and arguments list as parameters
3. Function calls `find_command_path()` and handles `CommandNotFoundError` appropriately
4. Function calls `generate_prompt()` and handles `TemplateReadError` appropriately
5. Function returns final processed prompt string
6. All error conditions are properly propagated with context information
7. Function includes comprehensive docstring with examples
