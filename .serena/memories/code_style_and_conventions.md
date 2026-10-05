# PromptCraft code conventions

Use idiomatic Go, `gofmt`, typed application errors and dependency injection for clock, filesystem and clipboard tests. Code names, comments and commit messages are English. User conversations are Brazilian Portuguese.

Keep template processing and filesystem actions in `internal/core`; the TUI owns navigation and rendering only. Preserve CLI flags, template syntax and error codes. Validate terminal-cell geometry, focus routing and unsaved-change safety in interactive changes.

Each commit must be one self-contained, buildable logical change. Use `go test -race ./...` and `golangci-lint run ./...` before completion. Runtime dependencies are managed by `go.mod`; version is in `internal/version/version.go`.
