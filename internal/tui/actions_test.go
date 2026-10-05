package tui

import (
	"path/filepath"
	"strings"
	"testing"
	"time"

	tea "github.com/charmbracelet/bubbletea"
)

func TestToastExpiresAfterItsTTL(t *testing.T) {
	app, _, _ := testApp(t)
	model := NewModel(app)

	now := time.Unix(1700000000, 0)
	app.Now = func() time.Time { return now }

	home := currentScreen(app).(*HomeScreen)
	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'f'}}) // notify information (no TTL)
	if app.toast == nil {
		t.Fatal("information notifications must be recorded")
	}

	home.status = "pending"
	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'d'}}) // no selection -> warning with TTL
	if app.toast == nil || app.toast.Severity != "warning" {
		t.Fatalf("expected a warning toast, got %+v", app.toast)
	}

	now = now.Add(9 * time.Second)
	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'x'}})
	if app.toast != nil {
		t.Fatalf("the toast must expire after 8 seconds: %+v", app.toast)
	}

	// The view renders the status line and the footer keymap.
	rendered := normalizeGolden(model.View())
	if !strings.Contains(rendered, "pending") || !strings.Contains(rendered, "q quit") {
		t.Fatalf("view is missing the status line or the keymap:\n%s", rendered)
	}
}

func TestRunShortcutOnlyFiresWhenTheFieldIsNotFocused(t *testing.T) {
	app, _, sent := testApp(t)
	model := NewModel(app)

	writeTemplate(t, filepath.Join(app.core.ProjectDir(), "copy.md"), "text $ARGUMENTS")
	home := currentScreen(app).(*HomeScreen)
	refresh(app, home)

	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'r'}})
	run := currentScreen(app).(*RunScreen)
	if !run.input.Focused() {
		t.Fatal("the arguments field must keep focus while typing")
	}

	// Typing 's' inserts it; the copy shortcut does not run.
	for _, r := range "s" {
		press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{r}})
	}
	if len(*sent) != 0 {
		t.Fatalf("typing must not trigger the shortcut: %v", *sent)
	}

	press(app, model, tea.KeyMsg{Type: tea.KeyTab})
	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'s'}})
	if len(*sent) != 1 || (*sent)[0] != "text s" {
		t.Fatalf("the copy shortcut must run when the field is not focused: %v", *sent)
	}

	// Back without copying returns to home.
	press(app, model, tea.KeyMsg{Type: tea.KeyEscape})
	if _, ok := currentScreen(app).(*HomeScreen); !ok {
		t.Fatalf("esc must return to home, got %T", currentScreen(app))
	}
}

func TestModalClosesOnEnterAndResultScrolls(t *testing.T) {
	app, _, _ := testApp(t)
	model := NewModel(app)

	writeTemplate(t, filepath.Join(app.core.ProjectDir(), "long.md"), strings.Repeat("line\n", 40))
	home := currentScreen(app).(*HomeScreen)
	refresh(app, home)

	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'v'}})
	if _, ok := currentScreen(app).(*VersionScreen); !ok {
		t.Fatalf("v must open the version panel, got %T", currentScreen(app))
	}
	press(app, model, tea.KeyMsg{Type: tea.KeyEnter})
	if _, ok := currentScreen(app).(*HomeScreen); !ok {
		t.Fatalf("enter must close a modal, got %T", currentScreen(app))
	}

	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'r'}})
	run := currentScreen(app).(*RunScreen)
	if !run.input.Focused() {
		t.Fatal("the arguments field must keep focus while typing")
	}
	press(app, model, tea.KeyMsg{Type: tea.KeyTab})
	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'d'}})
	result, ok := currentScreen(app).(*ResultScreen)
	if !ok {
		t.Fatalf("d must show the result, got %T", currentScreen(app))
	}

	before := result.viewport.YOffset
	press(app, model, tea.KeyMsg{Type: tea.KeyDown})
	if result.viewport.YOffset == before {
		t.Fatal("the result viewport must scroll on down")
	}
}

func TestHomeInitializeOpensTheSummaryPanel(t *testing.T) {
	app, _, _ := testApp(t)
	model := NewModel(app)

	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'i'}})
	panel, ok := currentScreen(app).(*InitResultScreen)
	if !ok {
		t.Fatalf("i must open the initialization panel, got %T", currentScreen(app))
	}
	if len(panel.result.Created) != 1 || len(panel.result.Existing) != 1 {
		t.Fatalf("the panel must show what was created: %+v", panel.result)
	}
	rendered := normalizeGolden(panel.View())
	if !strings.Contains(rendered, "Created example template: exemplo.md") {
		t.Fatalf("panel content: %q", rendered)
	}
}

func TestHomeSelectsAndRunsTheHighlightedTemplate(t *testing.T) {
	app, _, sent := testApp(t)
	model := NewModel(app)

	writeTemplate(t, filepath.Join(app.core.ProjectDir(), "one.md"), "# One\nfirst")
	writeTemplate(t, filepath.Join(app.core.UserDir(), "two.md"), "# Two\nsecond")

	home := currentScreen(app).(*HomeScreen)
	refresh(app, home)

	press(app, model, tea.KeyMsg{Type: tea.KeyDown})
	if len(home.templates) != 2 {
		t.Fatalf("both scopes must be listed: %+v", home.templates)
	}
	if !strings.Contains(normalizeGolden(model.View()), "[Global]") {
		t.Fatalf("the highlighted row must show its source:\n%s", normalizeGolden(model.View()))
	}

	press(app, model, tea.KeyMsg{Type: tea.KeyEnter})
	run, ok := currentScreen(app).(*RunScreen)
	if !ok {
		t.Fatalf("enter must open the run form, got %T", currentScreen(app))
	}
	if run.template.Name != "two" {
		t.Fatalf("the highlighted template must be run, got %q", run.template.Name)
	}

	press(app, model, tea.KeyMsg{Type: tea.KeyTab})
	press(app, model, tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'s'}})
	if len(*sent) != 1 || (*sent)[0] != "# Two\nsecond" {
		t.Fatalf("running must copy the generated prompt: %v", *sent)
	}
}
