package tui

import (
	"flag"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"testing"
	"time"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/x/exp/teatest"

	"github.com/quantmind-br/promptcraft/internal/clipboard"
	"github.com/quantmind-br/promptcraft/internal/core"
)

// rewriteGolden is named apart from teatest's own -update flag.
var rewriteGolden = flag.Bool("rewrite-golden", false, "rewrite the golden files")

// ansiPattern matches colour and cursor escape sequences so golden files store
// plain text that stays stable across terminals.
var ansiPattern = regexp.MustCompile("\x1b[\\[()][0-9;?]*[A-Za-z]|\x1b][^\x07\x1b]*(?:\x07|\x1b\\\\)")

// tempPathPattern matches the temporary directory shown in rendered paths,
// including truncated ones.
var tempPathPattern = regexp.MustCompile(`/tmp/[^\s│]*`)

func normalizeGolden(text string) string {
	plain := ansiPattern.ReplaceAllString(text, "")
	plain = tempPathPattern.ReplaceAllString(plain, "<temp>")
	return strings.TrimSpace(plain)
}

func requireGolden(t *testing.T, name, got string) {
	t.Helper()
	path := filepath.Join("testdata", "golden", name+".txt")
	if *rewriteGolden {
		if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, []byte(got+"\n"), 0o644); err != nil {
			t.Fatal(err)
		}
		return
	}

	want, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("missing golden file %s: %v", path, err)
	}
	if normalizeGolden(string(want)) != got {
		t.Fatalf("golden diff for %s:\n got:\n%s\nwant:\n%s", name, got, normalizeGolden(string(want)))
	}
}

// goldenApp builds an app with a fixed size and no clipboard side effects.
func goldenApp(t *testing.T) *App {
	t.Helper()
	root := t.TempDir()
	project := filepath.Join(root, "project")
	user := filepath.Join(root, "user")
	for _, dir := range []string{project, user} {
		if err := os.MkdirAll(filepath.Join(dir, ".promptcraft", "commands"), 0o755); err != nil {
			t.Fatal(err)
		}
	}

	processor := &core.Processor{
		Cwd:  func() (string, error) { return project, nil },
		Home: func() (string, error) { return user, nil },
		Now:  func() time.Time { return time.Unix(1700000000, 0).UTC() },
	}

	deps := clipboard.Deps{
		// A terminal-only route keeps the golden output deterministic.
		Env:         map[string]string{"PROMPTCRAFT_CLIPBOARD": "osc52"},
		FileExists:  func(path string) bool { return false },
		NativeCopy:  func(text string) error { return nil },
		OSC52Writer: func(text string) error { return nil },
	}

	app := NewApp(processor, deps, &strings.Builder{})
	app.width, app.height = 60, 14
	return app
}

func TestGoldenHomeWithTemplates(t *testing.T) {
	app := goldenApp(t)
	writeTemplate(t, filepath.Join(app.core.ProjectDir(), "review.md"), "# Code review")
	writeTemplate(t, filepath.Join(app.core.UserDir(), "commit.md"), "# Conventional commit")

	model := NewModel(app)
	home := currentScreen(app).(*HomeScreen)
	refresh(app, home)
	home.status = "✓ Deleted /review [Project]."

	requireGolden(t, "home_with_templates", normalizeGolden(model.View()))
}

func TestGoldenHomeEmpty(t *testing.T) {
	app := goldenApp(t)
	model := NewModel(app)

	requireGolden(t, "home_empty", normalizeGolden(model.View()))
}

func TestGoldenRunScreen(t *testing.T) {
	app := goldenApp(t)
	writeTemplate(t, filepath.Join(app.core.ProjectDir(), "review.md"), "# Code review")

	model := NewModel(app)
	home := currentScreen(app).(*HomeScreen)
	refresh(app, home)

	model.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'r'}})
	run := currentScreen(app).(*RunScreen)
	run.input.SetValue("main.py")
	model.Update(tea.KeyMsg{Type: tea.KeyEnter})

	requireGolden(t, "run_screen", normalizeGolden(model.View()))
}

func TestGoldenResultScreen(t *testing.T) {
	app := goldenApp(t)
	writeTemplate(t, filepath.Join(app.core.ProjectDir(), "review.md"), "Review $ARGUMENTS")

	model := NewModel(app)
	home := currentScreen(app).(*HomeScreen)
	refresh(app, home)

	model.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'r'}})
	run := currentScreen(app).(*RunScreen)
	run.input.SetValue("main.py")
	model.Update(tea.KeyMsg{Type: tea.KeyTab}) // leave the field so d works
	model.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'d'}})

	requireGolden(t, "result_screen", normalizeGolden(model.View()))
}

func TestGoldenTemplateEditor(t *testing.T) {
	app := goldenApp(t)
	writeTemplate(t, filepath.Join(app.core.ProjectDir(), "note.md"), "# Note")

	model := NewModel(app)
	home := currentScreen(app).(*HomeScreen)
	refresh(app, home)

	model.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'e'}})
	editor := currentScreen(app).(*TemplateScreen)
	editor.status = "⚠ Template 'note' already exists in the Project scope. Press Ctrl+S again to overwrite it."

	requireGolden(t, "template_editor", normalizeGolden(model.View()))
}

func TestGoldenModals(t *testing.T) {
	app := goldenApp(t)
	model := NewModel(app)

	home := currentScreen(app).(*HomeScreen)
	refresh(app, home)
	home.status = "✓ Project structure ready (see details)."
	model.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'i'}})
	requireGolden(t, "init_panel", normalizeGolden(model.View()))

	model.Update(tea.KeyMsg{Type: tea.KeyEscape})
	model.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'v'}})
	requireGolden(t, "version_panel", normalizeGolden(model.View()))

	model.Update(tea.KeyMsg{Type: tea.KeyEscape})
	model.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'?'}})
	requireGolden(t, "help_panel", normalizeGolden(model.View()))
}

// TestProgramDrivesTheScreenStack runs the model through a real Bubble Tea
// program (teatest) and checks that keys reach the screen stack.
func TestProgramDrivesTheScreenStack(t *testing.T) {
	app := goldenApp(t)
	writeTemplate(t, filepath.Join(app.core.ProjectDir(), "review.md"), "# Code review")

	home := currentScreen(app).(*HomeScreen)
	refresh(app, home)

	model := NewModel(app)
	tm := teatest.NewTestModel(t, model, teatest.WithInitialTermSize(60, 14))

	teatest.WaitFor(t, tm.Output(), func(out []byte) bool {
		return strings.Contains(normalizeGolden(string(out)), "Code review")
	}, teatest.WithDuration(5*time.Second))

	tm.Send(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'n'}})
	teatest.WaitFor(t, tm.Output(), func(out []byte) bool {
		return strings.Contains(normalizeGolden(string(out)), "New template")
	}, teatest.WithDuration(5*time.Second))

	if _, ok := currentScreen(app).(*TemplateScreen); !ok {
		t.Fatalf("the program must push the editor, got %T", currentScreen(app))
	}

	if err := tm.Quit(); err != nil {
		t.Fatal(err)
	}
	tm.WaitFinished(t, teatest.WithFinalTimeout(5*time.Second))

}
