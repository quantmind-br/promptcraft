# PromptCraft Product Requirements Document (PRD)

## Goals and Background Context

### Goals
- Enable developers to create reusable prompt templates through simple slash commands
- Reduce prompt creation time by 80% (from ~30 seconds to <5 seconds) 
- Achieve cross-platform compatibility (Windows, macOS, Linux) with <150ms execution time
- Provide hierarchical command discovery (project overrides global templates)
- Establish foundation for team standardization of AI interactions

### Background Context

PromptCraft addresses the critical inefficiency where developers repeatedly type complex instructions to AI assistants, leading to time waste, inconsistencies across teams, and loss of optimized prompt patterns. The current landscape lacks a universal, AI-agnostic solution for prompt management.

The tool functions as a "prompt compiler" that transforms slash commands into complex prompts using file-based templates, leveraging developer-familiar workflows while enabling both individual productivity and team standardization.

### Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-09-01 | 1.0 | Initial PRD creation from Project Brief | Mary (Business Analyst) |

## Requirements

### Functional

1. **FR1:** The system shall discover command templates by searching `.promptcraft/commands/` directories in hierarchical order (current project → global home directory)

2. **FR2:** The system shall process Markdown template files containing `$ARGUMENTS` placeholders and substitute them with user-provided arguments

3. **FR3:** The CLI shall accept slash commands in the format `promptcraft /command-name arg1 arg2 argN`

4. **FR4:** The system shall copy generated prompts to the system clipboard automatically using cross-platform clipboard integration

5. **FR5:** The system shall provide a `--stdout` flag option to output prompts to terminal instead of clipboard

6. **FR6:** The system shall include an `--init` command that creates the `.promptcraft/commands/` directory structure with example templates

7. **FR7:** The system shall provide a `--list` command that displays all available commands from both project and global directories with descriptions

8. **FR8:** The system shall handle missing commands gracefully by displaying user-friendly error messages

9. **FR9:** The system shall support command templates with descriptive first-line comments that serve as command descriptions

10. **FR10:** The system shall prioritize project-level commands over global commands when naming conflicts occur

### Non Functional

1. **NFR1:** Command execution time must be under 150ms for immediate productivity impact

2. **NFR2:** The system must work identically across Windows, macOS, and Linux platforms

3. **NFR3:** The application must have minimal dependencies (only click, pyperclip as production dependencies)

4. **NFR4:** The system must never crash with unhandled exceptions - all errors must be caught and presented as user-friendly messages

5. **NFR5:** Code must follow PEP 8 standards with comprehensive docstrings for all functions and classes

6. **NFR6:** The tool must have zero external service dependencies - operates entirely with local file system

7. **NFR7:** Memory footprint must remain minimal with no persistent processes or background services

8. **NFR8:** The system must provide 95%+ test coverage across all core functionality

## User Interface Design Goals

### Overall UX Vision
PromptCraft provides a frictionless CLI experience that feels native to developer workflows. The interface prioritizes speed and simplicity, with intuitive command discovery and clear error messaging that guides users toward success.

### Key Interaction Paradigms
- **Slash Command Interface:** Familiar `/command` syntax that mirrors popular tools like Slack and Discord
- **File-Based Configuration:** Leverage developers' existing comfort with file-based configuration and version control
- **Smart Defaults:** Zero-configuration operation with sensible fallbacks and helpful initialization
- **Progressive Disclosure:** Basic functionality works immediately, advanced features discoverable through help and listing

### Core Screens and Views
- **Command Execution View:** Primary interaction showing command processing and success/error feedback
- **Command Listing View:** Organized display of available commands with descriptions and source locations
- **Initialization View:** Setup process creating directory structure and example templates
- **Help Interface:** Comprehensive usage instructions and examples

### Accessibility: None
CLI tool inherently provides screen reader compatibility through standard terminal interfaces.

### Branding
Minimal, professional CLI aesthetic focusing on clarity and speed. Error messages use color coding (red for errors, green for success) following terminal conventions.

### Target Device and Platforms: Cross-Platform
Terminal/command line interface supporting Windows Command Prompt, PowerShell, macOS Terminal, and Linux shells (bash, zsh, etc.).

## Technical Assumptions

### Repository Structure: Monorepo
Single repository containing the complete Python package with standardized `src/` layout for clean packaging and distribution.

### Service Architecture
**Monolithic CLI Application:** Single-binary design with modular internal structure (core logic, CLI interface, exception handling) to maintain fast startup times and simple deployment.

### Testing Requirements
**Full Testing Pyramid:** Unit tests for core logic, integration tests for CLI interface using click's CliRunner, and end-to-end tests for file system interactions and cross-platform compatibility.

### Additional Technical Assumptions and Requests
- Python 3.10+ requirement for modern syntax features and performance optimizations
- Setuptools with pyproject.toml for modern Python packaging standards
- Cross-platform file path handling using pathlib for robust file system operations
- Template discovery must respect .gitignore patterns to avoid scanning irrelevant directories
- Error messages must be localized to English with clear, actionable guidance

## Epic List

### Epic 1: Foundation & Core Command Processing
Establish project infrastructure and implement the core template discovery and processing engine that transforms slash commands into generated prompts.

### Epic 2: CLI Interface & User Experience  
Build the complete command-line interface with argument parsing, error handling, and user-friendly interactions including initialization and command listing features.

### Epic 3: Cross-Platform Integration & Distribution
Implement clipboard integration, ensure cross-platform compatibility, create comprehensive test coverage, and prepare the package for distribution.

## Epic 1: Foundation & Core Command Processing

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

## Epic 2: CLI Interface & User Experience

**Epic Goal:** Create a complete, user-friendly command-line interface that provides intuitive access to all PromptCraft functionality including command execution, initialization, listing, and helpful error messaging that guides users toward successful outcomes.

### Story 2.1: Basic CLI Framework and Command Execution

As a user,
I want to execute slash commands through a clean CLI interface,
so that I can generate prompts quickly and efficiently.

#### Acceptance Criteria
1. Click-based CLI application with main group command `promptcraft`
2. Primary command accepts format: `promptcraft /command-name arg1 arg2 argN`
3. Command strips leading slash from command name before processing
4. Successfully processed prompts are copied to clipboard using pyperclip
5. Success message displayed: "✅ Prompt for '/command-name' copied to clipboard!"
6. Green color coding used for success messages using click.secho
7. CLI includes proper help text and usage examples

### Story 2.2: Error Handling and User Feedback

As a user,
I want clear, helpful error messages when things go wrong,
so that I can understand and fix issues quickly.

#### Acceptance Criteria
1. `CommandNotFoundError` displays user-friendly message in red: "❌ Command '/command-name' not found"
2. `TemplateReadError` displays file-specific error message with path information
3. All error messages use red color coding with click.secho
4. Generic exceptions are caught and displayed as "❌ Unexpected error occurred"
5. Error messages suggest next steps (e.g., "Run 'promptcraft --list' to see available commands")
6. Application never crashes with unhandled exception tracebacks
7. Exit codes are appropriate (0 for success, 1 for errors)

### Story 2.3: Output Mode Selection with --stdout Flag

As a user,
I want the option to output prompts to terminal instead of clipboard,
so that I can use the tool in different workflows and environments.

#### Acceptance Criteria
1. `--stdout` flag option available for the main command
2. When `--stdout` used, prompt is printed to terminal instead of copied to clipboard
3. Success message changes to: "✅ Prompt for '/command-name' generated:"
4. Prompt content is displayed with proper formatting/indentation
5. No clipboard interaction occurs when `--stdout` flag is used
6. Flag is properly documented in help text
7. Flag works in combination with all other functionality

### Story 2.4: Project Initialization Command

As a user,
I want an initialization command that sets up the project structure,
so that I can start using PromptCraft immediately in a new project.

#### Acceptance Criteria
1. `promptcraft --init` command creates `.promptcraft/commands/` directory in current directory
2. Command creates example template file `exemplo.md` with instructive content
3. Example template demonstrates `$ARGUMENTS` usage and provides guidance
4. Command reports what directories and files were created
5. Command handles case where directories already exist gracefully
6. Success message: "✅ PromptCraft initialized! Created .promptcraft/commands/ with example template"
7. Command includes helpful next steps in output

### Story 2.5: Command Listing and Discovery

As a user,
I want to see all available commands with descriptions,
so that I can discover and use the templates available to me.

#### Acceptance Criteria
1. `promptcraft --list` command scans both project and global command directories
2. Lists all `.md` files found with their command names (without .md extension)
3. Shows source location for each command (Project/Global)
4. Displays first line of each template file as description (if available)
5. Output formatted as clean table or list with proper alignment
6. Handles empty directories gracefully with appropriate message
7. Commands sorted alphabetically for easy scanning

## Epic 3: Cross-Platform Integration & Distribution

**Epic Goal:** Ensure robust cross-platform functionality with comprehensive clipboard integration, create thorough test coverage for reliability, and prepare the package for easy installation and distribution across all target platforms.

### Story 3.1: Cross-Platform Clipboard Integration

As a user on any operating system,
I want clipboard functionality to work reliably,
so that I can use PromptCraft seamlessly regardless of my platform.

#### Acceptance Criteria
1. Pyperclip integration works correctly on Windows (cmd, PowerShell)
2. Clipboard functionality verified on macOS Terminal
3. Linux clipboard support confirmed across major distributions
4. Graceful fallback behavior if clipboard access fails
5. Error message displayed if clipboard unavailable: "⚠️ Clipboard unavailable, use --stdout instead"
6. No platform-specific code paths - pyperclip handles all platform differences
7. Clipboard operations don't block or timeout command execution

### Story 3.2: Comprehensive Test Suite

As a developer,
I want complete test coverage across all functionality,
so that the tool is reliable and regression-free across all platforms.

#### Acceptance Criteria
1. Unit tests for all core.py functions with pytest
2. CLI integration tests using click.testing.CliRunner
3. File system interaction tests using temporary directories
4. Error condition tests for all custom exceptions
5. Cross-platform path handling tests using pathlib
6. Mock tests for clipboard functionality to avoid dependencies
7. Test coverage above 95% as measured by coverage.py
8. Tests executable via `pytest` command with clear pass/fail reporting

### Story 3.3: Command Performance and Optimization

As a user,
I want extremely fast command execution,
so that the tool doesn't interrupt my development flow.

#### Acceptance Criteria
1. Cold start execution time under 150ms measured on standard hardware
2. Warm execution (second command) under 100ms
3. File system operations optimized to minimize disk I/O
4. Lazy loading of modules where possible to reduce import time
5. Memory usage remains minimal throughout execution
6. No unnecessary file scanning or directory traversal
7. Performance benchmarking tests included in test suite

### Story 3.4: Package Distribution Preparation

As a user,
I want easy installation through standard Python packaging tools,
so that I can install and update PromptCraft effortlessly.

#### Acceptance Criteria
1. `pyproject.toml` configured for setuptools with proper metadata
2. Console script entry point `promptcraft` properly configured
3. Package installable via `pip install .` from source
4. All dependencies correctly specified with appropriate version constraints
5. Package metadata includes description, author, license, keywords
6. `README.md` includes installation instructions and basic usage examples
7. Version number managed in single location (__init__.py or pyproject.toml)

### Story 3.5: Documentation and User Guide

As a user,
I want comprehensive documentation and examples,
so that I can effectively use all features of PromptCraft.

#### Acceptance Criteria
1. `README.md` includes complete installation instructions
2. Documentation covers all CLI commands with examples
3. Template creation guide with multiple example scenarios
4. Troubleshooting section addressing common issues
5. Examples show both individual and team usage patterns
6. Template format specification clearly documented
7. Contributing guidelines for future development

## Checklist Results Report

*[This section will be populated with PM checklist results after review]*

## Next Steps

### UX Expert Prompt
Review this PRD focusing on the CLI user experience design. The tool targets developer workflows with emphasis on speed and simplicity. Please evaluate the interaction patterns, error messaging, and command discovery mechanisms for optimal developer productivity.

### Architect Prompt
This PRD defines PromptCraft, a Python CLI tool for prompt template management. Please enter architecture mode to design the technical implementation following the specified tech stack (Python 3.10+, click, pyperclip, pytest) and non-functional requirements (sub-150ms performance, cross-platform compatibility). Focus on clean modular design enabling the epic-driven development approach outlined in the requirements.