package tui

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	tea "github.com/charmbracelet/bubbletea"
)

func TestQuitKeyStaysAvailableToTheTextFields(t *testing.T) {
	app, _, _ := testApp(t)
	model := NewModel(app)

	writeTemplate(t, filepath.Join(app.core.ProjectDir(), "note.md"), "# Note")
	home := currentScreen(app).(*HomeScreen)
	refresh(app, home)

	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'n'}})
	editor := currentScreen(app).(*TemplateScreen)

	// q typed in the name field is content, not a shortcut.
	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'q'}})
	if editor.name.Value() != "q" {
		t.Fatalf("the field must receive the key: %q", editor.name.Value())
	}
	if _, ok := currentScreen(app).(*TemplateScreen); !ok {
		t.Fatalf("typing q must not leave the editor, got %T", currentScreen(app))
	}

	// With the scope selector focused, q is a shortcut again.
	press(app, model, tea.KeyMsg{Type: tea.KeyTab})
	if editor.focus != "scope" {
		t.Fatalf("tab must move focus to the scope selector, got %q", editor.focus)
	}
	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'q'}})
	if !editor.discardPending {
		t.Fatal("unsaved content requires discard confirmation")
	}
	press(app, model, tea.KeyMsg{Type: tea.KeyEscape})
	if _, ok := currentScreen(app).(*HomeScreen); !ok {
		t.Fatalf("q outside a text field must go back, got %T", currentScreen(app))
	}

	// Escape keeps priority even while a field is focused.
	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'r'}})
	run := currentScreen(app).(*RunScreen)
	if !run.input.Focused() {
		t.Fatal("the run form must focus its field")
	}
	for _, r := range "q" {
		press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{r}})
	}
	if run.input.Value() != "q" {
		t.Fatalf("q must reach the arguments field: %q", run.input.Value())
	}
	press(app, model, tea.KeyMsg{Type: tea.KeyEscape})
	if _, ok := currentScreen(app).(*HomeScreen); !ok {
		t.Fatalf("esc must return to home, got %T", currentScreen(app))
	}
}

func TestMovingTheCursorDropsAPendingDeleteConfirmation(t *testing.T) {
	app, _, _ := testApp(t)
	model := NewModel(app)

	home := currentScreen(app).(*HomeScreen)
	writeTemplate(t, filepath.Join(app.core.ProjectDir(), "a.md"), "# A")
	writeTemplate(t, filepath.Join(app.core.ProjectDir(), "b.md"), "# B")
	refresh(app, home)

	if len(home.templates) != 2 {
		t.Fatalf("two templates must be listed: %+v", home.templates)
	}

	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'d'}}) // arms A
	if home.confirmedDelete == "" {
		t.Fatal("the first press must arm the confirmation")
	}

	press(app, model, tea.KeyMsg{Type: tea.KeyDown}) // moves to B
	if home.confirmedDelete != "" {
		t.Fatalf("moving the cursor must drop the confirmation: %q", home.confirmedDelete)
	}

	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'d'}}) // arms B
	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'d'}}) // confirms B
	if _, err := os.Stat(filepath.Join(app.core.ProjectDir(), "b.md")); !os.IsNotExist(err) {
		t.Fatalf("B must be deleted: %v", err)
	}
	if _, err := os.Stat(filepath.Join(app.core.ProjectDir(), "a.md")); err != nil {
		t.Fatalf("A must survive the confirmation on B: %v", err)
	}
}

func TestPushedScreenIsInitializedAndHomeRefreshesOnReturn(t *testing.T) {
	app, _, _ := testApp(t)
	model := NewModel(app)

	home := currentScreen(app).(*HomeScreen)
	refresh(app, home)

	// The initialization panel must report its result through Init.
	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'i'}})
	if _, ok := currentScreen(app).(*InitResultScreen); !ok {
		t.Fatalf("i must open the panel, got %T", currentScreen(app))
	}
	if app.toast == nil || app.toast.Message != "Project structure ready." {
		t.Fatalf("the pushed screen must run its Init: %+v", app.toast)
	}

	// Creating a template through the editor refreshes the home list on return.
	press(app, model, tea.KeyMsg{Type: tea.KeyEscape})
	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'n'}})
	editor := currentScreen(app).(*TemplateScreen)
	if editor.mode != "create" {
		t.Fatalf("n must open the editor in create mode, got %q", editor.mode)
	}
	for _, r := range "new" {
		press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{r}})
	}
	press(app, model, tea.KeyMsg{Type: tea.KeyTab})
	press(app, model, tea.KeyMsg{Type: tea.KeyTab}) // content
	for _, r := range "# New template" {
		if r == ' ' {
			press(app, model, tea.KeyMsg{Type: tea.KeySpace})
			continue
		}
		press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{r}})
	}
	press(app, model, tea.KeyMsg{Type: tea.KeyCtrlS})

	if _, ok := currentScreen(app).(*HomeScreen); !ok {
		t.Fatalf("saving returns to home, got %T", currentScreen(app))
	}
	rendered := normalizeGolden(model.View())
	if !strings.Contains(rendered, "new") {
		t.Fatalf("the home list must show the saved template:\n%s", rendered)
	}
}

func TestToastSchedulesAnExpiryCommand(t *testing.T) {
	app, _, _ := testApp(t)
	model := NewModel(app)

	now := time.Unix(1700000000, 0)
	app.Now = func() time.Time { return now }

	home := currentScreen(app).(*HomeScreen)
	refresh(app, home)

	_, cmd := model.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'d'}})
	if app.toast == nil || cmd == nil {
		t.Fatal("a new warning must schedule an expiry command")
	}
	_, repeat := model.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'x'}})
	if repeat != nil {
		t.Fatal("an existing toast must not schedule duplicate timers")
	}

	// Advancing the clock past the TTL clears it on the next message.
	now = now.Add(9 * time.Second)
	model.Update(nil)
	if app.toast != nil {
		t.Fatalf("the toast must expire: %+v", app.toast)
	}
}

func TestTextBufKeepsTheCaretInsideItsWidth(t *testing.T) {
	buf := NewTextBuf(strings.Repeat("x", 40), 10, 3)
	buf.Focused = true
	buf.CaretCol = 25

	plain := normalizeGolden(buf.View())
	if !strings.Contains(plain, "x") {
		t.Fatal("the window must render content")
	}
	for _, line := range strings.Split(plain, "\n") {
		if len([]rune(line)) > 10 {
			t.Fatalf("the window must respect the buffer width: %q", line)
		}
	}
}
