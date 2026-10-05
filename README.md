# PromptCraft

Reusable Markdown prompts, a fast CLI and a keyboard-first terminal workspace.
PromptCraft is a standalone Go application: no interpreter, virtual environment or background service is needed.

## Install

Requires **Go 1.24.2 or newer** to build. The compiled binary runs on Linux, macOS and Windows.

```sh
go install github.com/quantmind-br/promptcraft/cmd/promptcraft@latest
```

Or build from the repository:

```sh
git clone https://github.com/quantmind-br/promptcraft.git
cd promptcraft
make install
```

`make install` installs or updates `~/.local/bin/promptcraft`. Add that directory to `PATH`, or choose another destination:

```sh
make install BIN_DIR=/usr/local/bin
make uninstall
```

Without Make (including Windows):

```sh
go build -o promptcraft ./cmd/promptcraft
# Windows: go build -o promptcraft.exe ./cmd/promptcraft
```

## Quick start

```sh
promptcraft --init
promptcraft                         # interactive workspace (TTY required)
promptcraft --list
promptcraft exemplo "describe the change"
promptcraft --stdout exemplo "describe the change"
```

Templates are ordinary `.md` files in:

- `.promptcraft/commands/` — templates for the current project;
- `~/.promptcraft/commands/` — personal templates available in every project.

A project template overrides a user template with the same name. Names can be supplied with or without a leading slash.

### Write a template

Save `.promptcraft/commands/review.md`:

```markdown
# Code review
Review $ARGUMENTS for correctness, security and maintainability.
Explain each finding and suggest a concrete fix.
```

Then run:

```sh
promptcraft review "internal/core"
promptcraft --stdout /review "internal/core"
```

The first line supplies the description in the library. `$ARGUMENTS` inserts the full argument text. Indexed placeholders are zero-based:

```markdown
Compare $ARGUMENTS[0] with $ARGUMENTS[1].
```

```sh
promptcraft --stdout compare before after
```

Out-of-range indexes are replaced with empty text. The interactive arguments field supplies its full text as a single argument; use the CLI for separate indexed arguments.

## Interactive workspace

Run `promptcraft` without arguments in a terminal.

- **Template library:** search names, descriptions and sources; preview the selected template; create, edit, delete or initialize the project.
- **Responsive dashboard:** side-by-side library and preview on wide terminals, stacked preview when space permits, compact list on smaller terminals.
- **Run form:** visible field/action focus; generate and copy, or preview without copying.
- **Result:** wrapped read-only text, scroll progress and clipboard retry. Copying always uses the original text, never its wrapped presentation.
- **Editor:** project/user scope, visible caret, undo/redo and unsaved-change protection. Renaming or changing scope moves the template; overwrites and deletions require confirmation.
- **Help and setup:** scrollable panels and contextual keyboard hints.

| Screen | Keys | Action |
|---|---|---|
| Library | `↑/↓`, `j/k`, `PgUp/PgDn` | Select or browse templates |
| Library | `/`, `Ctrl+F` | Search; `Enter` applies, `Esc` clears |
| Library | `Enter`, `r` | Open the selected template |
| Library | `n`, `e`, `d` | Create, edit, delete (repeat `d` to confirm) |
| Library | `i`, `f`, `v`, `?` | Setup, refresh, about, keyboard guide |
| Run | `Enter`, `Ctrl+S` | Generate and copy |
| Run | `Ctrl+P` | Generate and preview without copying |
| Run | `Tab`, `Shift+Tab` | Cycle field and actions |
| Result/help | `↑/↓`, `PgUp/PgDn`, `Home/End` | Scroll |
| Result | `c` | Copy or retry |
| Editor | `Tab`, `Shift+Tab` | Next/previous field |
| Editor | `Ctrl+S`, `Ctrl+D` | Save or delete; confirm destructive actions |
| Editor | `Ctrl+Z`, `Ctrl+Y` | Undo/redo content edits |
| Editor | `Esc` | Go back; repeat to discard unsaved changes |
| Global | `Ctrl+Q`, `Ctrl+C` | Quit; unsaved changes require confirmation |

Minimum terminal size: **40 columns × 12 rows**. A normal **80 × 24** terminal is recommended; **100 × 30** or larger enables the full dashboard.

## Clipboard

PromptCraft attempts the native clipboard and falls back to **OSC 52** through the terminal for SSH/headless sessions. Native clipboard utilities may need to be installed for your platform. Terminal clipboard support and permissions are controlled by your terminal.

```sh
PROMPTCRAFT_CLIPBOARD=osc52 promptcraft review "changes"
PROMPTCRAFT_CLIPBOARD=native promptcraft review "changes"
```

OSC 52 is fire-and-forget: “sent” does not guarantee the terminal accepted the copy. If copying fails, the CLI prints the prompt, or use `--stdout` explicitly. In the TUI, use `Ctrl+P` to preview and select the text. OSC 52 payloads are limited to 192 KiB.

## CLI options

```text
promptcraft [OPTIONS] [COMMAND_NAME] [ARGUMENTS...]

--init       Create project directories and an example (preserve existing files)
--list       List available templates and their sources
--stdout     Print generated prompt instead of copying
--version    Report the installed version
--help       Show CLI help
```

Failures to read/process templates, initialize directories or write output return a nonzero exit code. Template deletion is restricted to authorized template roots, including symlink checks.

## Development

```sh
make build
make test                       # go test -race ./...
make lint                       # golangci-lint run ./...
go test -coverprofile=coverage.out ./...
go tool cover -func=coverage.out
```

CI builds and tests Go on Linux, macOS and Windows, with a total coverage gate of 85%.
Unit and regression tests cover template processing, filesystem guards, clipboard routing and TUI interactions. Integration tests build and execute the CLI in isolated directories. Golden snapshots protect screen rendering:

```sh
go test ./internal/tui -rewrite-golden
```

Review golden diffs before accepting changes. Keep CLI compatibility and template data intact when evolving the interface.

```text
cmd/promptcraft/       executable entry point
internal/cli/         Cobra CLI and output handling
internal/core/        template discovery, processing, caching and filesystem actions
internal/clipboard/   native and OSC 52 delivery
internal/tui/         Bubble Tea screens, theme, editor and regression snapshots
internal/style/       CLI color helpers
internal/version/     version source
internal/apperror/    typed application errors
tests/integration/    built-binary CLI contract tests
docs/architecture.md  current implementation architecture
```

## Troubleshooting

- **Command not found:** check `PATH`, `go env GOPATH` and the installation destination.
- **No templates:** use `--init`, create a `.md` template, or check the current working directory; `f` refreshes the library after external changes.
- **Clipboard unavailable:** install native clipboard tools, enable OSC 52 in the terminal, or use `--stdout` / TUI preview.
- **Terminal too small:** resize it; narrow layouts intentionally omit the preview.
- **Read/write denied:** check template directory permissions. Failed reads are shown read-only in the editor and cannot overwrite the file.

For bugs, include the PromptCraft version, OS, terminal name, exact command/key sequence and a minimal reproducible template. Do not include confidential prompt content.
