// Package parity compares the Go port with the legacy Python implementation on
// the same fixtures. It is skipped when the legacy tree or a Python interpreter
// with click installed is not available.
package parity

import (
	"bytes"
	"errors"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func legacyRoot() string {
	cwd, err := os.Getwd()
	if err != nil {
		return ""
	}
	// tests/parity -> repo root -> legacy/python
	return filepath.Join(filepath.Dir(filepath.Dir(cwd)), "legacy", "python")
}

func skipWithoutLegacy(t *testing.T) {
	t.Helper()
	python := pythonCommand()
	if _, err := exec.LookPath(python); err != nil {
		t.Skipf("%s is not available", python)
	}
	if err := exec.Command(python, "-c", "import click").Run(); err != nil {
		t.Skipf("the legacy implementation needs click: %v", err)
	}
	if _, err := os.Stat(filepath.Join(legacyRoot(), "src", "promptcraft", "main.py")); err != nil {
		t.Skip("the legacy Python implementation is not available")
	}
}

func pythonCommand() string {
	if value := os.Getenv("PROMPTCRAFT_LEGACY_PYTHON"); value != "" {
		return value
	}
	return "python3"
}

type scenario struct {
	name  string
	args  []string
	files map[string]string // template files inside the project scope
	env   map[string]string
}

// prepare creates an isolated working directory (also used as HOME) with the
// scenario fixtures.
func prepare(t *testing.T, scenario scenario) string {
	t.Helper()
	root := t.TempDir()
	project := filepath.Join(root, ".promptcraft", "commands")
	if err := os.MkdirAll(project, 0o755); err != nil {
		t.Fatal(err)
	}
	for name, content := range scenario.files {
		if err := os.WriteFile(filepath.Join(project, name), []byte(content), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	return root
}

func environment(root string, scenario scenario) []string {
	env := append(os.Environ(), "HOME="+root)
	for key, value := range scenario.env {
		env = append(env, key+"="+value)
	}
	return env
}

func normalize(text string) string {
	return strings.TrimSpace(strings.ReplaceAll(text, "\r\n", "\n"))
}

func exitCode(err error) int {
	if err == nil {
		return 0
	}
	var exitErr *exec.ExitError
	if errors.As(err, &exitErr) {
		return exitErr.ExitCode()
	}
	return 1
}

func runGo(t *testing.T, binary string, scenario scenario) (string, int) {
	t.Helper()
	root := prepare(t, scenario)

	cmd := exec.Command(binary, scenario.args...)
	cmd.Dir = root
	cmd.Env = environment(root, scenario)

	var out bytes.Buffer
	cmd.Stdout = &out
	cmd.Stderr = &out
	err := cmd.Run()
	return normalize(out.String()), exitCode(err)
}

func runPython(t *testing.T, scenario scenario) (string, int) {
	t.Helper()
	root := prepare(t, scenario)

	args := append([]string{"-m", "promptcraft"}, scenario.args...)
	cmd := exec.Command(pythonCommand(), args...)
	cmd.Dir = root
	cmd.Env = append(environment(root, scenario), "PYTHONPATH="+filepath.Join(legacyRoot(), "src"))

	var out bytes.Buffer
	cmd.Stdout = &out
	cmd.Stderr = &out
	err := cmd.Run()
	return normalize(out.String()), exitCode(err)
}

var cases = []scenario{
	{
		name: "arguments substitution",
		args: []string{"--stdout", "review", "main.py", "today"},
		files: map[string]string{
			"review.md": "# Code review\n\nReview $ARGUMENTS\n",
		},
	},
	{
		name: "indexed arguments",
		args: []string{"--stdout", "two", "first", "second"},
		files: map[string]string{
			"two.md": "Indexed: $ARGUMENTS[1] and $ARGUMENTS[0], out of range: $ARGUMENTS[4]\n",
		},
	},
	{
		name: "no arguments",
		args: []string{"--stdout", "plain"},
		files: map[string]string{
			"plain.md": "# Plain\n\nGot: [$ARGUMENTS]\n",
		},
	},
	{
		name: "command not found",
		args: []string{"--stdout", "absent"},
	},
	{
		name: "list with templates in both scopes",
		args: []string{"--list"},
		files: map[string]string{
			"alpha.md": "# Alpha desc\n",
			"beta.md":  "plain description line\n",
		},
	},
	{
		name: "empty list",
		args: []string{"--list"},
	},
	{
		name: "init output",
		args: []string{"--init"},
	},
	{
		name: "clipboard disabled falls back to stdout",
		args: []string{"greet", "world"},
		files: map[string]string{
			"greet.md": "hello $ARGUMENTS\n",
		},
		env: map[string]string{"CI": "true"},
	},
	{
		name: "version output",
		args: []string{"--version"},
	},
}

func TestParityWithLegacyPython(t *testing.T) {
	skipWithoutLegacy(t)

	binary := filepath.Join(t.TempDir(), "promptcraft-go")
	build := exec.Command("go", "build", "-o", binary, "github.com/quantmind-br/promptcraft/cmd/promptcraft")
	if output, err := build.CombinedOutput(); err != nil {
		t.Fatalf("building the Go port failed: %v\n%s", err, output)
	}

	for _, scenario := range cases {
		t.Run(scenario.name, func(t *testing.T) {
			got, gotCode := runGo(t, binary, scenario)
			want, wantCode := runPython(t, scenario)
			if got != want || gotCode != wantCode {
				t.Fatalf("parity mismatch\n go:   %q (exit %d)\n py:   %q (exit %d)", got, gotCode, want, wantCode)
			}
		})
	}
}
