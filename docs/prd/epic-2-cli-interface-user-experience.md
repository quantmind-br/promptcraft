# Epic 2: CLI Interface & User Experience

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
