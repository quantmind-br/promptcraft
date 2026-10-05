# PromptCraft development commands

```sh
make install
make build
make test
make lint
go test -coverprofile=coverage.out ./...
go tool cover -func=coverage.out
go test ./internal/tui -rewrite-golden
```

Review golden diffs before accepting them. Integration tests under `tests/integration` build and run the Go binary in isolated directories. Go modules in `go.mod`/`go.sum` supply dependencies.
