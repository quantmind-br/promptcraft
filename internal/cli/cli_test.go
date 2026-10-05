package cli

import (
	"bytes"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/quantmind-br/promptcraft/internal/clipboard"
	"github.com/quantmind-br/promptcraft/internal/core"
)

func testOptions(t *testing.T) (Options, *bytes.Buffer) {
	t.Helper()
	root := t.TempDir()
	project := filepath.Join(root, "project")
	user := filepath.Join(root, "user")

	buffer := &bytes.Buffer{}
	env := map[string]string{"DISPLAY": ":0", "X11_SOCKET": "yes"}
	options := Options{
		Out: buffer,
		Core: &core.Processor{
			Cwd:  func() (string, error) { return project, nil },
			Home: func() (string, error) { return user, nil },
			Now:  time.Now,
		},
		Deps: clipboard.Deps{
			Env:         env,
			FileExists:  func(path string) bool { return path == "/tmp/.X11-unix" && env["X11_SOCKET"] == "yes" },
			NativeCopy:  func(text string) error { return nil },
			OSC52Writer: func(text string) error { return nil },
		},
		IsInteractive: func() bool { return false },
	}
	return options, buffer
}

func writeTemplate(t *testing.T, path, content string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
}

func TestVersionAndHelpMatchTheLegacyText(t *testing.T) {
	options, buffer := testOptions(t)
	if code := Run([]string{"--version"}, options); code != 0 {
		t.Fatalf("exit code %d", code)
	}
	if strings.TrimSpace(buffer.String()) != "PromptCraft, version 0.1.0" {
		t.Fatalf("version output: %q", buffer.String())
	}

	buffer.Reset()
	if code := Run([]string{"--help"}, options); code != 0 {
		t.Fatalf("exit code %d", code)
	}
	help := buffer.String()
	for _, fragment := range []string{"PromptCraft CLI", "Usage Examples:", "--stdout    Output to terminal instead of clipboard"} {
		if !strings.Contains(help, fragment) {
			t.Fatalf("help is missing %q:\n%s", fragment, help)
		}
	}
}

func TestListCommands(t *testing.T) {
	options, buffer := testOptions(t)

	if code := Run([]string{"--list"}, options); code != 0 {
		t.Fatalf("exit code %d", code)
	}
	output := buffer.String()
	if !strings.Contains(output, "No commands found") || !strings.Contains(output, "Run 'promptcraft --init' to create examples.") {
		t.Fatalf("empty list output: %q", output)
	}

	projectDir := options.Core.ProjectDir()
	userDir := options.Core.UserDir()
	writeTemplate(t, filepath.Join(projectDir, "alpha.md"), "# Alpha desc")
	writeTemplate(t, filepath.Join(userDir, "beta.md"), "# Beta desc")

	buffer.Reset()
	if code := Run([]string{"--list"}, options); code != 0 {
		t.Fatalf("exit code %d", code)
	}
	lines := strings.Split(strings.TrimSpace(buffer.String()), "\n")
	if len(lines) != 6 {
		t.Fatalf("unexpected table:\n%s", buffer.String())
	}
	if lines[0] != "Available Commands (2 found):" {
		t.Fatalf("header mismatch: %q", lines[0])
	}
	if !strings.Contains(lines[4], "alpha") || !strings.Contains(lines[4], "Project") || !strings.Contains(lines[4], "Alpha desc") {
		t.Fatalf("project row mismatch: %q", lines[4])
	}
	if !strings.Contains(lines[5], "beta") || !strings.Contains(lines[5], "Global") {
		t.Fatalf("user row mismatch: %q", lines[5])
	}
}

func TestInitProjectOutput(t *testing.T) {
	options, buffer := testOptions(t)

	if code := Run([]string{"--init"}, options); code != 0 {
		t.Fatalf("exit code %d", code)
	}
	output := buffer.String()
	for _, fragment := range []string{
		"✅ PromptCraft initialized! Created .promptcraft/commands/ with example template",
		"📁 Project structure:",
		"  • Created directory: .promptcraft/commands/",
		"  • Created example template: exemplo.md",
		"👉 Next steps:",
		"  1. Try the example: promptcraft exemplo 'hello world'",
	} {
		if !strings.Contains(output, fragment) {
			t.Fatalf("init output is missing %q:\n%s", fragment, output)
		}
	}

	// A second run reports what already exists and never rewrites the template.
	buffer.Reset()
	if code := Run([]string{"--init"}, options); code != 0 {
		t.Fatalf("exit code %d", code)
	}
	output = buffer.String()
	if !strings.Contains(output, "Directory already exists: .promptcraft/commands/") ||
		!strings.Contains(output, "Example template already exists: exemplo.md") {
		t.Fatalf("second init output: %q", output)
	}
}

func TestCommandExecutionWritesToStdoutWithFlag(t *testing.T) {
	options, buffer := testOptions(t)
	writeTemplate(t, filepath.Join(options.Core.ProjectDir(), "greet.md"), "hello $ARGUMENTS")

	if code := Run([]string{"greet", "world", "again"}, options); code != 0 {
		t.Fatalf("exit code %d", code)
	}
	output := buffer.String()
	if !strings.Contains(output, "✅ Prompt for '/greet' copied to clipboard!") {
		t.Fatalf("native copy message missing: %q", output)
	}

	buffer.Reset()
	if code := Run([]string{"--stdout", "/greet", "x"}, options); code != 0 {
		t.Fatalf("exit code %d", code)
	}
	output = buffer.String()
	if !strings.Contains(output, "✅ Prompt for '/greet' generated:") || !strings.Contains(output, "hello x\n") {
		t.Fatalf("stdout output: %q", output)
	}
}

func TestClipboardRoutesReportTheirOwnMessages(t *testing.T) {
	options, buffer := testOptions(t)
	writeTemplate(t, filepath.Join(options.Core.ProjectDir(), "cmd.md"), "prompt text")

	for key := range options.Deps.Env {
		delete(options.Deps.Env, key)
	}
	options.Deps.Env["HERDR_ENV"] = "1"
	options.Deps.OSC52Writer = func(text string) error { return nil }

	if code := Run([]string{"cmd"}, options); code != 0 {
		t.Fatalf("exit code %d", code)
	}
	if !strings.Contains(buffer.String(), "✅ Prompt for '/cmd' sent to clipboard via terminal (OSC 52)!") {
		t.Fatalf("OSC 52 message missing: %q", buffer.String())
	}

	buffer.Reset()
	options.Deps.Env["DISPLAY"] = ":0"
	options.Deps.Env["X11_SOCKET"] = "yes"
	options.Deps.NativeCopy = func(text string) error { return errors.New("no backend") }
	options.Deps.OSC52Writer = func(text string) error { return errors.New("not a terminal") }

	if code := Run([]string{"cmd"}, options); code != 0 {
		t.Fatalf("exit code %d", code)
	}
	output := buffer.String()
	if !strings.Contains(output, "⚠️ Clipboard unavailable, use --stdout instead") ||
		!strings.Contains(output, "✅ Prompt for '/cmd' generated:") ||
		!strings.Contains(output, "prompt text") {
		t.Fatalf("fallback output: %q", output)
	}
}

func TestCommandNotFoundAndMissingName(t *testing.T) {
	options, buffer := testOptions(t)

	if code := Run([]string{"absent"}, options); code != 1 {
		t.Fatalf("missing command must exit 1, got %d", code)
	}
	output := buffer.String()
	if !strings.Contains(output, "❌ Command '/absent' not found") ||
		!strings.Contains(output, "Run 'promptcraft --list' to see available commands") {
		t.Fatalf("not-found output: %q", output)
	}

	buffer.Reset()
	if code := Run([]string{}, options); code != 1 {
		t.Fatalf("missing name must exit 1, got %d", code)
	}
	output = buffer.String()
	if !strings.Contains(output, "❌ Command name is required") ||
		!strings.Contains(output, "Use 'promptcraft --help' for usage information") {
		t.Fatalf("missing-name output: %q", output)
	}

	// In an interactive terminal the same call opens the interface.
	buffer.Reset()
	launched := false
	options.IsInteractive = func() bool { return true }
	options.LaunchTUI = func() error {
		launched = true
		return errors.New("boom")
	}
	if code := Run([]string{}, options); code != 1 {
		t.Fatalf("a failed TUI launch must exit 1, got %d", code)
	}
	if !launched {
		t.Fatal("the TUI must be launched for an interactive no-argument run")
	}
	output = buffer.String()
	if !strings.Contains(output, "Interactive interface unavailable: boom") ||
		!strings.Contains(output, "Run 'promptcraft --help' for command-line usage") {
		t.Fatalf("TUI failure output: %q", output)
	}

	// --stdout keeps a non-interactive run on the CLI path.
	buffer.Reset()
	options.IsInteractive = func() bool { return false }
	if code := Run([]string{"--stdout"}, options); code != 1 {
		t.Fatalf("exit code %d", code)
	}
	if !strings.Contains(buffer.String(), "❌ Command name is required") {
		t.Fatalf("non-interactive output: %q", buffer.String())
	}
}

func TestTemplateReadErrorIsReported(t *testing.T) {
	options, buffer := testOptions(t)
	writeTemplate(t, filepath.Join(options.Core.ProjectDir(), "binary.md"), "text\x00bytes")

	if code := Run([]string{"binary"}, options); code != 1 {
		t.Fatalf("exit code %d", code)
	}
	if !strings.Contains(buffer.String(), "❌ Command 'binary' template processing failed: Failed to decode template file") {
		t.Fatalf("error output: %q", buffer.String())
	}
}
