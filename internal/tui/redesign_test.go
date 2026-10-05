package tui

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/x/ansi"
	"github.com/quantmind-br/promptcraft/internal/core"
)

func TestLibrarySearchKeepsTypingAndSelectionSafe(t *testing.T) {
	app, _, _ := testApp(t)
	model := NewModel(app)
	for name, content := range map[string]string{"query.md": "# Query planner", "review.md": "# Security audit", "other.md": "# Other"} {
		writeTemplate(t, filepath.Join(app.core.ProjectDir(), name), content)
	}
	home := app.Current().(*HomeScreen)
	refresh(app, home)
	if home.selected() == nil || home.details == "" {
		t.Fatal("first template must be selected immediately")
	}
	press(app, model, keyMsg('/'))
	for _, r := range "query" {
		press(app, model, keyMsg(r))
	}
	if app.quitting || len(home.templates) != 1 || home.selected().Name != "query" {
		t.Fatalf("search stole a shortcut or wrong selection: %+v", home.templates)
	}
	press(app, model, tea.KeyMsg{Type: tea.KeyEnter})
	if home.search.Focused() {
		t.Fatal("enter must apply the search")
	}
	press(app, model, tea.KeyMsg{Type: tea.KeyEnter})
	if app.Current().(*RunScreen).template.Name != "query" {
		t.Fatal("filtered selection must drive the action")
	}
	press(app, model, tea.KeyMsg{Type: tea.KeyEscape})
	press(app, model, keyMsg('/'))
	home.search.SetValue("nonexistent")
	home.applyFilter("")
	if home.selected() != nil || !strings.Contains(home.View(), "No matches") {
		t.Fatal("no matches must not retain a stale selection")
	}
	press(app, model, tea.KeyMsg{Type: tea.KeyEscape})
	if len(home.templates) != 3 || home.search.Value() != "" {
		t.Fatal("escape must clear search, not quit")
	}
	press(app, model, keyMsg('/'))
	for _, r := range "security" {
		press(app, model, keyMsg(r))
	}
	if len(home.templates) != 1 || home.selected().Name != "review" {
		t.Fatal("search must include descriptions")
	}
}

func TestRunFocusCyclesAndPreviewDoesNotCopy(t *testing.T) {
	app, _, sent := testApp(t)
	model := NewModel(app)
	writeTemplate(t, filepath.Join(app.core.ProjectDir(), "run.md"), "Prompt $ARGUMENTS")
	refresh(app, app.Current().(*HomeScreen))
	press(app, model, keyMsg('r'))
	run := app.Current().(*RunScreen)
	press(app, model, keyMsg('q'))
	if run.input.Value() != "q" {
		t.Fatal("printable quit key must reach the input")
	}
	press(app, model, tea.KeyMsg{Type: tea.KeyTab})
	press(app, model, tea.KeyMsg{Type: tea.KeyTab})
	if run.action != 1 || run.input.Focused() {
		t.Fatal("second tab selects preview")
	}
	press(app, model, tea.KeyMsg{Type: tea.KeyTab})
	if !run.input.Focused() {
		t.Fatal("third tab must return to input")
	}
	press(app, model, tea.KeyMsg{Type: tea.KeyShiftTab})
	if run.action != 1 {
		t.Fatal("reverse tab selects last action")
	}
	press(app, model, tea.KeyMsg{Type: tea.KeyEnter})
	if _, ok := app.Current().(*ResultScreen); !ok || len(*sent) != 0 {
		t.Fatal("preview must show the result without clipboard delivery")
	}
	press(app, model, keyMsg('c'))
	if len(*sent) != 1 || (*sent)[0] != "Prompt q" {
		t.Fatalf("result copy: %v", *sent)
	}
	press(app, model, tea.KeyMsg{Type: tea.KeyEscape})
	press(app, model, tea.KeyMsg{Type: tea.KeyShiftTab})
	press(app, model, tea.KeyMsg{Type: tea.KeyShiftTab})
	if !run.input.Focused() {
		t.Fatal("reverse cycling must reach input")
	}
	press(app, model, tea.KeyMsg{Type: tea.KeyCtrlP})
	if len(*sent) != 1 {
		t.Fatal("Ctrl+P must never copy")
	}
}

func TestEditorProtectsDirtyStateAndInvalidatesConfirmations(t *testing.T) {
	app, _, _ := testApp(t)
	model := NewModel(app)
	path := filepath.Join(app.core.ProjectDir(), "note.md")
	writeTemplate(t, path, "# Original")
	refresh(app, app.Current().(*HomeScreen))
	press(app, model, keyMsg('e'))
	editor := app.Current().(*TemplateScreen)
	if editor.dirty() {
		t.Fatal("loaded template is clean")
	}
	press(app, model, tea.KeyMsg{Type: tea.KeyShiftTab})
	if editor.focus != "content" {
		t.Fatal("reverse focus cycles into content")
	}
	press(app, model, keyMsg('x'))
	press(app, model, tea.KeyMsg{Type: tea.KeyEscape})
	if !editor.discardPending {
		t.Fatal("first escape must ask before losing data")
	}
	press(app, model, keyMsg('y'))
	if editor.discardPending {
		t.Fatal("editing must cancel discard confirmation")
	}
	press(app, model, tea.KeyMsg{Type: tea.KeyCtrlQ})
	if !editor.quitPending || app.quitting {
		t.Fatal("quit must protect unsaved changes")
	}
	press(app, model, tea.KeyMsg{Type: tea.KeyEscape})
	if editor.quitPending {
		t.Fatal("escape cancels quit confirmation")
	}
	press(app, model, tea.KeyMsg{Type: tea.KeyCtrlS})
	if _, ok := app.Current().(*HomeScreen); !ok {
		t.Fatal("save returns to library")
	}
	content, err := os.ReadFile(path)
	if err != nil || !strings.HasPrefix(string(content), "xy") {
		t.Fatalf("save: %q %v", content, err)
	}
	press(app, model, keyMsg('n'))
	editor = app.Current().(*TemplateScreen)
	editor.name.SetValue("note")
	editor.content = NewTextBuf("replacement", 40, 4)
	press(app, model, tea.KeyMsg{Type: tea.KeyCtrlS})
	if editor.confirmedTarget == "" {
		t.Fatal("overwrite must be armed")
	}
	press(app, model, keyMsg('z'))
	if editor.confirmedTarget != "" {
		t.Fatal("changing the target must invalidate overwrite confirmation")
	}
	press(app, model, tea.KeyMsg{Type: tea.KeyCtrlQ})
	press(app, model, tea.KeyMsg{Type: tea.KeyCtrlQ})
	if !app.quitting {
		t.Fatal("confirmed quit must leave")
	}
}

func TestUnreadableEditorCannotOverwrite(t *testing.T) {
	app, _, _ := testApp(t)
	path := filepath.Join(app.core.ProjectDir(), "missing.md")
	editor := NewTemplateScreen(app, "edit", core.CommandInfo{Name: "missing", Path: path, Source: core.SourceProject})
	if !editor.readOnly {
		t.Fatal("read failure must be read-only")
	}
	editor.changeFocus(-1)
	editor.Update(keyMsg('q'))
	editor.save()
	if editor.content.Text() != "" {
		t.Fatal("read-only buffer must reject typing")
	}
	if _, err := os.Stat(path); !os.IsNotExist(err) {
		t.Fatal("failed load must not be replaced with an empty file")
	}
}

func TestHelpScrollsAndKeepsItsConcreteScreenType(t *testing.T) {
	app, _, _ := testApp(t)
	model := NewModel(app)
	press(app, model, keyMsg('?'))
	panel := app.Current().(*HelpScreen)
	press(app, model, tea.KeyMsg{Type: tea.KeyEnd})
	if _, ok := app.Current().(*HelpScreen); !ok {
		t.Fatal("panel updates must preserve its identity")
	}
	if panel.viewport.YOffset == 0 || !strings.Contains(panel.View(), "GLOBAL") {
		t.Fatal("help must scroll to every section")
	}
	press(app, model, tea.KeyMsg{Type: tea.KeyHome})
	if panel.viewport.YOffset != 0 {
		t.Fatal("home jumps to top")
	}
}

func TestResponsiveScreenGeometry(t *testing.T) {
	for _, size := range [][2]int{{40, 12}, {60, 14}, {80, 24}, {100, 30}, {140, 42}, {24, 8}} {
		t.Run(fmt.Sprint(size), func(t *testing.T) {
			app, _, _ := testApp(t)
			model := NewModel(app)
			writeTemplate(t, filepath.Join(app.core.ProjectDir(), "wide.md"), "# Unicode 界界界\n"+strings.Repeat("long content 界 ", 100))
			refresh(app, app.Current().(*HomeScreen))
			model.Update(tea.WindowSizeMsg{Width: size[0], Height: size[1]})
			screens := []Screen{app.Current(), NewRunScreen(app, app.Current().(*HomeScreen).templates[0]), NewResultScreen(app, "wide", strings.Repeat("界long ", 90), false), NewTemplateScreen(app, "create", core.CommandInfo{}), NewHelpScreen(app), NewVersionScreen(app), NewInitResultScreen(app, core.InitResult{})}
			for _, screen := range screens {
				app.stack = []Screen{screen}
				screen.Update(tea.WindowSizeMsg{Width: size[0], Height: size[1]})
				view := model.View()
				lines := strings.Split(view, "\n")
				if len(lines) > size[1] {
					t.Fatalf("%T height %d exceeds %d", screen, len(lines), size[1])
				}
				for _, line := range lines {
					if ansi.StringWidth(line) > size[0] {
						t.Fatalf("%T overflows: %q", screen, line)
					}
				}
				if size[0] >= 40 && !strings.Contains(view, "esc") && !strings.Contains(view, "quit") {
					t.Fatalf("%T hides navigation", screen)
				}
			}
		})
	}
}

func TestNotificationTimersIgnoreStaleMessages(t *testing.T) {
	app, _, _ := testApp(t)
	model := NewModel(app)
	now := time.Unix(100, 0)
	app.Now = func() time.Time { return now }
	model.Update(keyMsg('f'))
	first := app.toast.ExpiresAt
	now = now.Add(time.Second)
	model.Update(keyMsg('d'))
	second := app.toast.ExpiresAt
	model.Update(toastExpiredMsg{deadline: first})
	if app.toast == nil || app.toast.ExpiresAt != second {
		t.Fatal("old timer cannot clear the new notification")
	}
	model.Update(toastExpiredMsg{deadline: second})
	if app.toast != nil {
		t.Fatal("current timer must expire notification without keyboard input")
	}
}

func TestBufferPasteUndoRedoAndCellWidth(t *testing.T) {
	buf := NewTextBuf("", 6, 3)
	buf.Focused = true
	buf.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("界界\nhello\r\nworld\t!"), Paste: true})
	want := buf.Text()
	if want != "界界\nhello\nworld    !" {
		t.Fatalf("paste: %q", want)
	}
	buf.Update(tea.KeyMsg{Type: tea.KeyCtrlZ})
	if buf.Text() != "" {
		t.Fatal("paste must undo in one step")
	}
	buf.Update(tea.KeyMsg{Type: tea.KeyCtrlY})
	if buf.Text() != want {
		t.Fatal("redo restores text and cursor")
	}
	buf.Update(tea.KeyMsg{Type: tea.KeyHome})
	buf.Update(tea.KeyMsg{Type: tea.KeyDelete})
	if !strings.HasSuffix(buf.Text(), "orld    !") {
		t.Fatal("delete removes forward character")
	}
	for _, line := range strings.Split(buf.View(), "\n") {
		if ansi.StringWidth(line) > 6 {
			t.Fatalf("wide glyph overflow: %q", line)
		}
	}
	buf.CaretLine = 0
	buf.CaretCol = 2
	if ansi.StringWidth(buf.View()) == 0 {
		t.Fatal("end-of-line caret must remain visible")
	}
}
