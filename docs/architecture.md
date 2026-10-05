# PromptCraft architecture

PromptCraft is a standalone Go CLI with a Bubble Tea terminal interface. The current architecture is defined by `cmd/`, `internal/`, `go.mod` and the Go CI workflow.

## Boundaries

- `cmd/promptcraft` wires process I/O, terminal detection and the CLI exit code.
- `internal/cli` implements Cobra flags and stable output/error handling.
- `internal/core` discovers Markdown templates, applies project precedence, caches reads and substitutes full/indexed arguments. It owns filesystem validation and init/save/delete actions.
- `internal/clipboard` isolates native and OSC 52 delivery with injectable dependencies.
- `internal/tui` owns interactive state, navigation, responsive rendering and editing. Screens consume core/clipboard APIs, not CLI output strings.
- `internal/style`, `internal/version`, `internal/apperror` supply shared infrastructure.

## TUI state and rendering

`App` owns the screen stack and shared dependencies. `Model.Update` handles terminal resize, safe global quit, navigation and notification timers. Pushed screens receive current geometry and initialization; returning screens refresh their data. Inactive screens receive resize updates too.

`theme.go` defines adaptive semantic colors and terminal-cell-aware geometry. The full-screen shell reserves space for the header, content, notification and two rows of contextual shortcuts. Each screen handles its own scrolling; the shell bounds output as a final guard.

The library filters name/description/source and previews the current selection. The run form separates text entry from copy/preview actions. Result and information panels use viewports. The template editor tracks dirty state and bounded undo/redo; overwrite/delete/discard actions require explicit confirmation.

## Safety and compatibility

- Templates remain plain files in project and user `.promptcraft/commands` directories.
- CLI flags, substitution and exit codes remain stable.
- Read failures cannot silently overwrite an unreadable template.
- Delete guards validate template roots after resolving symlinks.
- Clipboard delivery never claims acknowledgment for OSC 52.
- Tests inject filesystem, clipboard and clock dependencies and use isolated temporary directories.

## Verification

Use `go test -race ./...`, `golangci-lint run ./...` and `go test -coverprofile=coverage.out ./...`. `tests/integration` builds the binary and checks CLI contracts without an interpreter. TUI golden files and responsive/interaction tests live in `internal/tui`.

Older planning material in the nested `architecture/`, `prd/`, `stories/` and `qa/` directories is historical, not a specification of the current implementation. See [documentation scope](README.md).
