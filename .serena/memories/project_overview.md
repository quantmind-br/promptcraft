# PromptCraft project overview

PromptCraft is a Go CLI and Bubble Tea terminal workspace for reusable Markdown prompt templates. Entry point: `cmd/promptcraft`. Runtime packages: `internal/cli`, `internal/core`, `internal/clipboard`, `internal/tui`, `internal/style`, `internal/version`, `internal/apperror`.

Project templates live in `.promptcraft/commands`; user templates live in `~/.promptcraft/commands`. Project templates take precedence. Build with Go 1.24.2 or newer and install using `make install`. No interpreter or legacy implementation is required.

Canonical guides: `README.md`, `APP.md`, `docs/architecture.md`. Older nested planning documents are historical; see `docs/README.md`.
