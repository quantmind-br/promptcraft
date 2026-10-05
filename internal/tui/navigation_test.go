package tui

import (
	"fmt"
	"path/filepath"
	"strings"
	"testing"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/x/ansi"
	"github.com/quantmind-br/promptcraft/internal/core"
)

func TestLibraryPaginationAndExternalRefresh(t *testing.T) {
	app, _, _ := testApp(t)
	model := NewModel(app)
	home := app.Current().(*HomeScreen)
	for i := 0; i < 20; i++ {
		writeTemplate(t, filepath.Join(app.core.ProjectDir(), fmt.Sprintf("item%02d.md", i)), "# Description")
	}
	refresh(app, home)
	press(app, model, tea.KeyMsg{Type: tea.KeyEnd})
	if home.selected().Name != "item19" {
		t.Fatal("end selects the final item")
	}
	if !strings.Contains(home.View(), "item19") {
		t.Fatal("last selected item must be visible")
	}
	press(app, model, tea.KeyMsg{Type: tea.KeyHome})
	press(app, model, tea.KeyMsg{Type: tea.KeyPgDown})
	if home.list.Index() == 0 {
		t.Fatal("page down must advance")
	}
	press(app, model, tea.KeyMsg{Type: tea.KeyPgUp})
	if home.list.Index() != 0 {
		t.Fatal("page up must return")
	}
	writeTemplate(t, filepath.Join(app.core.ProjectDir(), "external.md"), "# Created outside the app")
	press(app, model, keyMsg('f'))
	if len(home.templates) != 21 {
		t.Fatal("refresh must invalidate cached discovery")
	}
	model.Update(tea.WindowSizeMsg{Width: 100, Height: 30})
	if !strings.Contains(home.View(), "Preview") {
		t.Fatal("wide library needs a preview")
	}
	model.Update(tea.WindowSizeMsg{Width: 80, Height: 24})
	if !strings.Contains(home.View(), "Preview") {
		t.Fatal("standard library needs a stacked preview")
	}
}

func TestResizeInactiveScreensAndPreserveResultText(t *testing.T) {
	app, _, sent := testApp(t)
	model := NewModel(app)
	text := strings.Repeat("wide 界 content ", 50)
	writeTemplate(t, filepath.Join(app.core.ProjectDir(), "long.md"), text)
	refresh(app, app.Current().(*HomeScreen))
	press(app, model, keyMsg('r'))
	run := app.Current().(*RunScreen)
	press(app, model, tea.KeyMsg{Type: tea.KeyCtrlP})
	result := app.Current().(*ResultScreen)
	model.Update(tea.WindowSizeMsg{Width: 40, Height: 12})
	if result.viewport.Height < 1 || result.viewport.Width != 34 || run.input.Width != 31 {
		t.Fatal("every stacked screen must resize")
	}
	press(app, model, tea.KeyMsg{Type: tea.KeyEnd})
	if result.viewport.YOffset == 0 {
		t.Fatal("wrapped text must remain scrollable")
	}
	press(app, model, keyMsg('c'))
	if len(*sent) != 1 || (*sent)[0] != text {
		t.Fatal("copy must use original content, not wrapped presentation")
	}
	press(app, model, tea.KeyMsg{Type: tea.KeyEscape})
	if app.Current() != run {
		t.Fatal("back must preserve the resized run form")
	}
}

func TestScreenBodiesFitWithoutRelyingOnShellClipping(t *testing.T) {
	for _, size := range [][2]int{{40, 12}, {60, 14}, {80, 24}, {100, 30}} {
		app, _, _ := testApp(t)
		model := NewModel(app)
		model.Update(tea.WindowSizeMsg{Width: size[0], Height: size[1]})
		home := app.Current().(*HomeScreen)
		screens := []Screen{home, NewHelpScreen(app), NewVersionScreen(app), NewResultScreen(app, "result", strings.Repeat("line\n", 50), false), NewRunScreen(app, core.CommandInfo{Name: "test", Description: "Example description"}), NewTemplateScreen(app, "create", core.CommandInfo{})}
		for _, screen := range screens {
			lines := strings.Split(screen.View(), "\n")
			if len(lines) > app.bodyHeight() {
				t.Fatalf("%T at %v needs %d rows, has %d", screen, size, len(lines), app.bodyHeight())
			}
			for _, line := range lines {
				if ansi.StringWidth(line) > app.bodyWidth() {
					t.Fatalf("%T at %v overflows body width", screen, size)
				}
			}
		}
	}
}

func TestLongDescriptionsCannotHideRunInput(t *testing.T) {
	app, _, _ := testApp(t)
	screen := NewRunScreen(app, core.CommandInfo{Name: "long", Description: strings.Repeat("description ", 200)})
	screen.input.SetValue("VISIBLE_ARGUMENT")
	if !strings.Contains(screen.View(), "VISIBLE_ARGUMENT") || !strings.Contains(screen.View(), "Preview only") {
		t.Fatal("long metadata must not push the arguments or actions off screen")
	}
}
