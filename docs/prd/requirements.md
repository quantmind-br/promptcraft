# Requirements

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
