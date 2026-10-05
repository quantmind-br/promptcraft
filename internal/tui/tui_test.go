package tui

import (
	"bytes"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	tea "github.com/charmbracelet/bubbletea"

	"github.com/quantmind-br/promptcraft/internal/clipboard"
	"github.com/quantmind-br/promptcraft/internal/core"
)

func writeTemplate(t *testing.T, path, content string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
}

func testApp(t *testing.T) (*App, *bytes.Buffer, *[]string) {
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
		Now:  time.Now,
	}

	sent := []string{}
	deps := clipboard.Deps{
		Env: map[string]string{"PROMPTCRAFT_CLIPBOARD": "osc52"},
		OSC52Writer: func(text string) error {
			sent = append(sent, text)
			return nil
		},
	}

	app := NewApp(processor, deps, &bytes.Buffer{})
	// NewApp installs its own writer; tests record what it would send.
	app.deps.OSC52Writer = func(text string) error {
		sent = append(sent, text)
		return nil
	}
	app.width, app.height = 60, 14
	return app, &bytes.Buffer{}, &sent
}

func press(app *App, model *Model, key tea.KeyMsg) {
	model.Update(key)
}

func currentScreen(app *App) Screen { return app.Current() }

// refresh clears the discovery cache before repopulating, so tests do not
// depend on filesystem mtime granularity.
func refresh(app *App, home *HomeScreen) {
	app.core.InvalidateCaches()
	home.populateList("")
}

func TestHomeKeyDispatchPushesScreens(t *testing.T) {
	app, _, _ := testApp(t)
	model := NewModel(app)

	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'n'}})
	if _, ok := currentScreen(app).(*TemplateScreen); !ok {
		t.Fatalf("n must open the editor, got %T", currentScreen(app))
	}

	press(app, model, tea.KeyMsg{Type: tea.KeyEscape})
	if _, ok := currentScreen(app).(*HomeScreen); !ok {
		t.Fatalf("esc must return to home, got %T", currentScreen(app))
	}

	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'v'}})
	if _, ok := currentScreen(app).(*VersionScreen); !ok {
		t.Fatalf("v must open the version panel, got %T", currentScreen(app))
	}

	press(app, model, tea.KeyMsg{Type: tea.KeyEscape})
	if _, ok := currentScreen(app).(*HomeScreen); !ok {
		t.Fatalf("esc must close the version panel, got %T", currentScreen(app))
	}

	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'?'}})
	if _, ok := currentScreen(app).(*HelpScreen); !ok {
		t.Fatalf("? must open the help panel, got %T", currentScreen(app))
	}

	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'q'}})
	if _, ok := currentScreen(app).(*HelpScreen); ok {
		t.Fatal("q on a modal closes it")
	}
	if _, ok := currentScreen(app).(*HomeScreen); !ok {
		t.Fatalf("after closing the help panel home must be active, got %T", currentScreen(app))
	}

	model.Update(tea.KeyMsg{Type: tea.KeyCtrlQ})
	if !app.quitting {
		t.Fatal("ctrl+q must quit the program")
	}
}

func TestHomeDeleteNeedsTwoPressesAndRefreshesTheList(t *testing.T) {
	app, _, _ := testApp(t)
	model := NewModel(app)
	home := currentScreen(app).(*HomeScreen)

	writeTemplate(t, filepath.Join(app.core.ProjectDir(), "keep.md"), "# Keep")
	refresh(app, home)

	if len(home.templates) != 1 {
		t.Fatalf("template must be discovered: %+v", home.templates)
	}

	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'d'}})
	if !strings.Contains(home.status, "Press d again to confirm") {
		t.Fatalf("first press must ask for confirmation: %q", home.status)
	}
	if _, err := os.Stat(filepath.Join(app.core.ProjectDir(), "keep.md")); err != nil {
		t.Fatal("the file must still exist after the first press")
	}

	// Moving the cursor resets the pending confirmation.
	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'f'}})
	if home.confirmedDelete != "" {
		t.Fatal("refresh must clear the pending confirmation")
	}

	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'d'}})
	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'d'}})
	if _, err := os.Stat(filepath.Join(app.core.ProjectDir(), "keep.md")); !os.IsNotExist(err) {
		t.Fatalf("the second press must delete the template: %v", err)
	}
	if !strings.Contains(home.status, "✓ Deleted /keep [Project].") {
		t.Fatalf("delete status: %q", home.status)
	}

	// Esc cancels a pending confirmation instead of quitting.
	writeTemplate(t, filepath.Join(app.core.ProjectDir(), "again.md"), "# Again")
	refresh(app, home)
	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'d'}})
	press(app, model, tea.KeyMsg{Type: tea.KeyEscape})
	if home.confirmedDelete != "" || home.status != "Delete cancelled." {
		t.Fatalf("esc must cancel the confirmation: %q", home.status)
	}
	if app.quitting {
		t.Fatal("esc while a confirmation is pending must not quit")
	}
}

func TestRunScreenCopiesAndShowsTheResult(t *testing.T) {
	app, _, sent := testApp(t)
	model := NewModel(app)
	home := currentScreen(app).(*HomeScreen)

	writeTemplate(t, filepath.Join(app.core.ProjectDir(), "greet.md"), "hello $ARGUMENTS")
	refresh(app, home)

	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'r'}})
	run, ok := currentScreen(app).(*RunScreen)
	if !ok {
		t.Fatalf("r must open the run form, got %T", currentScreen(app))
	}

	run.input.SetValue("world")
	press(app, model, tea.KeyMsg{Type: tea.KeyEnter})
	if len(*sent) != 1 || (*sent)[0] != "hello world" {
		t.Fatalf("Enter must run the template and copy it: %v", *sent)
	}
	if !strings.Contains(run.status, "✓ Sent to clipboard via terminal (OSC 52, 11 chars).") {
		t.Fatalf("copy status: %q", run.status)
	}

	// Tab leaves the field so the single-letter shortcuts work.
	press(app, model, tea.KeyMsg{Type: tea.KeyTab})
	if run.input.Focused() {
		t.Fatal("tab must leave the arguments field")
	}

	// Typing a shortcut letter inside the field inserts it instead of acting.
	run.input.Focus()
	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'s'}})
	if run.input.Value() != "worlds" {
		t.Fatalf("letters must go to the focused field, got %q", run.input.Value())
	}

	press(app, model, tea.KeyMsg{Type: tea.KeyTab})
	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'d'}})
	result, ok := currentScreen(app).(*ResultScreen)
	if !ok {
		t.Fatalf("d must show the result on screen, got %T", currentScreen(app))
	}
	if result.content != "hello worlds" {
		t.Fatalf("result content: %q", result.content)
	}
	if !strings.Contains(result.status, "Clipboard was not used for this result") {
		t.Fatalf("a result that was not copied must say so: %q", result.status)
	}

	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'c'}})
	if len(*sent) != 2 || (*sent)[1] != "hello worlds" {
		t.Fatalf("c must copy the shown result: %v", *sent)
	}
	if !strings.Contains(result.status, "Sent to clipboard via terminal") {
		t.Fatalf("copy status after c: %q", result.status)
	}

	press(app, model, tea.KeyMsg{Type: tea.KeyEscape})
	if _, ok := currentScreen(app).(*RunScreen); !ok {
		t.Fatalf("esc returns to the run form, got %T", currentScreen(app))
	}
}

func TestRunScreenReportsClipboardFailure(t *testing.T) {
	app, _, _ := testApp(t)
	model := NewModel(app)

	app.deps.OSC52Writer = func(text string) error { return errWriter }
	home := currentScreen(app).(*HomeScreen)
	writeTemplate(t, filepath.Join(app.core.ProjectDir(), "copy.md"), "text")
	refresh(app, home)

	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'r'}})
	run := currentScreen(app).(*RunScreen)
	press(app, model, tea.KeyMsg{Type: tea.KeyEnter})
	if !strings.Contains(run.status, "✗ Could not copy to the clipboard") {
		t.Fatalf("failure status: %q", run.status)
	}
}

var errWriter = &writerError{}

type writerError struct{}

func (w *writerError) Error() string { return "terminal unavailable" }

func TestTemplateEditorSavesConfirmsOverwriteAndMoves(t *testing.T) {
	app, _, _ := testApp(t)
	model := NewModel(app)
	home := currentScreen(app).(*HomeScreen)

	// Create: letters typed in the name field must not trigger a shortcut.
	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'n'}})
	editor := currentScreen(app).(*TemplateScreen)
	for _, r := range "note" {
		press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{r}})
	}
	if editor.name.Value() != "note" {
		t.Fatalf("typing must reach the name field, got %q", editor.name.Value())
	}

	press(app, model, tea.KeyMsg{Type: tea.KeyTab}) // scope
	press(app, model, tea.KeyMsg{Type: tea.KeyTab}) // content
	if editor.focus != "content" {
		t.Fatalf("tab must cycle focus, got %q", editor.focus)
	}
	for _, r := range "# Note body" {
		press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{r}})
	}

	press(app, model, tea.KeyMsg{Type: tea.KeyCtrlS})
	savedPath := filepath.Join(app.core.ProjectDir(), "note.md")
	if _, err := os.Stat(savedPath); err != nil {
		t.Fatalf("the template must be saved: %v", err)
	}
	if content, err := os.ReadFile(savedPath); err != nil || string(content) != "# Note body" {
		t.Fatalf("saved content: %q", string(content))
	}

	// Overwriting an existing template needs a second Ctrl+S.
	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'n'}})
	editor = currentScreen(app).(*TemplateScreen)
	for _, r := range "note" {
		press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{r}})
	}
	press(app, model, tea.KeyMsg{Type: tea.KeyTab}) // scope
	press(app, model, tea.KeyMsg{Type: tea.KeyTab}) // content
	for _, r := range "second" {
		press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{r}})
	}
	press(app, model, tea.KeyMsg{Type: tea.KeyCtrlS})
	if !strings.Contains(editor.status, "Press Ctrl+S again to overwrite") {
		t.Fatalf("overwrite must be confirmed: %q", editor.status)
	}
	content, err := os.ReadFile(savedPath)
	if err != nil || string(content) != "# Note body" {
		t.Fatalf("the first Ctrl+S must not write: %q", string(content))
	}

	// Editing to another scope moves the template there.
	press(app, model, tea.KeyMsg{Type: tea.KeyEscape}) // close without writing
	refresh(app, home)
	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'e'}})
	editor = currentScreen(app).(*TemplateScreen)
	if editor.mode != "edit" {
		t.Fatalf("e must open the editor in edit mode, got %q", editor.mode)
	}
	press(app, model, tea.KeyMsg{Type: tea.KeyTab})  // focus the scope selector
	press(app, model, tea.KeyMsg{Type: tea.KeyDown}) // select the user scope
	press(app, model, tea.KeyMsg{Type: tea.KeyCtrlS})

	movedPath := filepath.Join(app.core.UserDir(), "note.md")
	if _, err := os.Stat(movedPath); err != nil {
		t.Fatalf("the move must write to the user scope: %v", err)
	}
	if _, err := os.Stat(savedPath); !os.IsNotExist(err) {
		t.Fatalf("the original project file must be removed: %v", err)
	}

	// Invalid names are refused before any write.
	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'n'}})
	editor = currentScreen(app).(*TemplateScreen)
	editor.name.SetValue("bad/name")
	press(app, model, tea.KeyMsg{Type: tea.KeyCtrlS})
	if !strings.Contains(editor.status, "Name cannot contain path separators") {
		t.Fatalf("invalid name status: %q", editor.status)
	}

	// Empty content is refused.
	editor.name.SetValue("valid")
	press(app, model, tea.KeyMsg{Type: tea.KeyCtrlS})
	if !strings.Contains(editor.status, "Content is required") {
		t.Fatalf("empty content status: %q", editor.status)
	}
}

func TestTrailingMdIsStrippedFromTheName(t *testing.T) {
	if got := core.NormalizeName("typed.md"); got != "typed" {
		t.Fatalf("normalization failed: %q", got)
	}
}
