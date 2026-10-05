package tui

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	tea "github.com/charmbracelet/bubbletea"

	"github.com/quantmind-br/promptcraft/internal/core"
)

func TestKeyNameNormalisesLetters(t *testing.T) {
	if got := keyName(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'R'}}); got != "r" {
		t.Fatalf("uppercase letters must match the keymap: %q", got)
	}
	if got := keyName(tea.KeyMsg{Type: tea.KeyEnter}); got != "enter" {
		t.Fatalf("special keys keep their name: %q", got)
	}
}

func TestRunScreenReportsProcessingErrors(t *testing.T) {
	app, _, _ := testApp(t)
	model := NewModel(app)

	writeTemplate(t, filepath.Join(app.core.ProjectDir(), "bad.md"), "ok\x00")
	home := currentScreen(app).(*HomeScreen)
	refresh(app, home)

	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'r'}})
	run := currentScreen(app).(*RunScreen)
	press(app, model, tea.KeyMsg{Type: tea.KeyEnter})

	if !strings.Contains(run.status, "✗") {
		t.Fatalf("a read failure must be shown on the run screen: %q", run.status)
	}
	if app.toast == nil || app.toast.Severity != "error" {
		t.Fatalf("the failure must also raise a toast: %+v", app.toast)
	}

	press(app, model, tea.KeyMsg{Type: tea.KeyEscape})
	if _, ok := currentScreen(app).(*HomeScreen); !ok {
		t.Fatalf("esc must return to home, got %T", currentScreen(app))
	}
}

func TestHomeWarnsWhenNothingIsSelected(t *testing.T) {
	app, _, _ := testApp(t)
	model := NewModel(app)

	home := currentScreen(app).(*HomeScreen)
	refresh(app, home)

	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'e'}})
	if app.toast == nil || app.toast.Severity != "warning" {
		t.Fatalf("editing with no selection must warn: %+v", app.toast)
	}

	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'d'}})
	if !strings.Contains(app.toast.Message, "Select the template to delete first") {
		t.Fatalf("deleting with no selection must warn: %+v", app.toast)
	}

	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'r'}})
	if !strings.Contains(app.toast.Message, "Select a template first") {
		t.Fatalf("running with no selection must warn: %+v", app.toast)
	}

	// The empty list explains how to get started.
	rendered := normalizeGolden(model.View())
	if !strings.Contains(rendered, "No templates found.") {
		t.Fatalf("empty home view: %q", rendered)
	}
}

func TestResultScreenCopyFailureIsReported(t *testing.T) {
	app, _, _ := testApp(t)
	model := NewModel(app)

	writeTemplate(t, filepath.Join(app.core.ProjectDir(), "show.md"), "content")
	home := currentScreen(app).(*HomeScreen)
	refresh(app, home)

	app.deps.OSC52Writer = func(text string) error { return errWriter }

	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'r'}})
	run := currentScreen(app).(*RunScreen)
	_ = run
	press(app, model, tea.KeyMsg{Type: tea.KeyTab})
	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'d'}})
	result := currentScreen(app).(*ResultScreen)

	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'c'}})
	if !strings.Contains(result.status, "Could not copy") {
		t.Fatalf("copy failure status: %q", result.status)
	}
}

func TestTemplateEditorDeleteNeedsConfirmationAndRemovesTheFile(t *testing.T) {
	app, _, _ := testApp(t)
	model := NewModel(app)

	path := filepath.Join(app.core.ProjectDir(), "note.md")
	writeTemplate(t, path, "# Note")

	home := currentScreen(app).(*HomeScreen)
	refresh(app, home)

	// A create-mode editor refuses deletion.
	create := NewTemplateScreen(app, "create", core.CommandInfo{})
	if create.mode != "create" {
		t.Fatalf("the editor must know its mode, got %q", create.mode)
	}

	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'e'}})
	editor := currentScreen(app).(*TemplateScreen)

	press(app, model, tea.KeyMsg{Type: tea.KeyCtrlD})
	if !strings.Contains(editor.status, "Press Ctrl+D again to confirm") {
		t.Fatalf("first delete press must ask for confirmation: %q", editor.status)
	}
	if _, err := os.Stat(path); err != nil {
		t.Fatalf("the file must survive the first press: %v", err)
	}

	press(app, model, tea.KeyMsg{Type: tea.KeyCtrlD})
	if _, err := os.Stat(path); !os.IsNotExist(err) {
		t.Fatalf("the confirmed delete must remove the file: %v", err)
	}
	if _, ok := currentScreen(app).(*HomeScreen); !ok {
		t.Fatalf("delete returns to home, got %T", currentScreen(app))
	}
}

func TestModelViewAndQuitStates(t *testing.T) {
	app, _, _ := testApp(t)
	model := NewModel(app)

	if model.Init() != nil {
		t.Fatal("screens start without commands in this implementation")
	}
	if strings.TrimSpace(model.View()) == "" {
		t.Fatal("the active screen must render before quitting")
	}

	press(app, model, tea.KeyMsg{Type: tea.KeyCtrlQ})
	if model.View() != "" {
		t.Fatalf("the view must be empty after quitting: %q", model.View())
	}
}
