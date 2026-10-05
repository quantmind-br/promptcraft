// Package integration tests the built CLI in an isolated filesystem without an interpreter.
package integration

import (
	"bytes"
	"errors"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func TestCLIContract(t *testing.T) {
	name := "promptcraft"
	if runtime.GOOS == "windows" {
		name += ".exe"
	}
	binary := filepath.Join(t.TempDir(), name)
	build := exec.Command("go", "build", "-o", binary, "github.com/quantmind-br/promptcraft/cmd/promptcraft")
	if output, err := build.CombinedOutput(); err != nil {
		t.Fatalf("build: %v\n%s", err, output)
	}
	cases := []struct {
		name  string
		args  []string
		files map[string]string
		want  string
		code  int
	}{
		{"arguments", []string{"--stdout", "review", "main.go", "today"}, map[string]string{"review.md": "Review $ARGUMENTS\n"}, "Review main.go today", 0},
		{"indexes", []string{"--stdout", "two", "first", "second"}, map[string]string{"two.md": "$ARGUMENTS[1] / $ARGUMENTS[0] / $ARGUMENTS[4]"}, "second / first /", 0},
		{"empty arguments", []string{"--stdout", "plain"}, map[string]string{"plain.md": "Got: [$ARGUMENTS]"}, "Got: []", 0},
		{"missing", []string{"--stdout", "absent"}, nil, "Command '/absent' not found", 1},
		{"list", []string{"--list"}, map[string]string{"alpha.md": "# Alpha description\n"}, "Alpha description", 0},
		{"empty list", []string{"--list"}, nil, "No commands found", 0},
		{"init", []string{"--init"}, nil, "PromptCraft initialized!", 0},
		{"clipboard fallback", []string{"greet", "world"}, map[string]string{"greet.md": "hello $ARGUMENTS"}, "hello world", 0},
		{"version", []string{"--version"}, nil, "PromptCraft, version", 0},
		{"help", []string{"--help"}, nil, "--stdout", 0},
	}
	for _, test := range cases {
		t.Run(test.name, func(t *testing.T) {
			root := t.TempDir()
			commands := filepath.Join(root, ".promptcraft", "commands")
			if err := os.MkdirAll(commands, 0o755); err != nil {
				t.Fatal(err)
			}
			for name, content := range test.files {
				if err := os.WriteFile(filepath.Join(commands, name), []byte(content), 0o644); err != nil {
					t.Fatal(err)
				}
			}
			cmd := exec.Command(binary, test.args...)
			cmd.Dir = root
			// Remove inherited clipboard/display overrides rather than adding duplicate keys.
			for _, entry := range os.Environ() {
				key, _, _ := strings.Cut(entry, "=")
				switch strings.ToUpper(key) {
				case "HOME", "USERPROFILE", "CI", "PROMPTCRAFT_CLIPBOARD", "DISPLAY", "WAYLAND_DISPLAY", "SSH_TTY", "SSH_CONNECTION":
					continue
				}
				cmd.Env = append(cmd.Env, entry)
			}
			cmd.Env = append(cmd.Env, "HOME="+root, "USERPROFILE="+root, "CI=true", "PROMPTCRAFT_NO_CLIPBOARD=true")
			var output bytes.Buffer
			cmd.Stdout, cmd.Stderr = &output, &output
			err := cmd.Run()
			code := 0
			if err != nil {
				var exit *exec.ExitError
				if !errors.As(err, &exit) {
					t.Fatal(err)
				}
				code = exit.ExitCode()
			}
			if code != test.code || !strings.Contains(output.String(), test.want) {
				t.Fatalf("got exit %d: %q; want exit %d containing %q", code, output.String(), test.code, test.want)
			}
			if test.name == "init" {
				if _, err := os.Stat(filepath.Join(commands, "exemplo.md")); err != nil {
					t.Fatal(err)
				}
			}
		})
	}
}
