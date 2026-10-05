# PromptCraft product specification

PromptCraft turns reusable Markdown templates into ready-to-use prompts for any AI assistant. It is a local, standalone Go application with a CLI and a keyboard-first Bubble Tea workspace.

## User workflows

1. Initialize project templates or use personal templates shared across projects.
2. Find a template by name, description or source and inspect its preview.
3. Supply argument text, generate a prompt, then copy or inspect it.
4. Create and edit templates with explicit scope and save feedback.
5. Confirm destructive operations and protect unsaved changes.

## Technology

- Go 1.24.2 or newer for building; one executable for distribution.
- Cobra for CLI parsing and Bubble Tea/Bubbles/Lip Gloss for the terminal UI.
- Filesystem templates; no database, accounts, web server or external model required.
- Native clipboard and terminal OSC 52 delivery.
- Go unit, integration, regression and golden tests.

CLI flags and template syntax are documented in [README.md](README.md). Architecture and development boundaries are documented in [docs/architecture.md](docs/architecture.md).
