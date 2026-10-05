package tui

import (
	"fmt"
	"strings"

	tea "github.com/charmbracelet/bubbletea"

	"github.com/quantmind-br/promptcraft/internal/core"
	"github.com/quantmind-br/promptcraft/internal/version"
)

// modal is the shared behaviour of the feedback panels.
type modal struct {
	app   *App
	lines []string
}

// Init reports the panel content when it opens.
func (m *modal) Init() tea.Cmd { return nil }

// Update closes the panel on Esc, q or Enter.
func (m *modal) Update(msg tea.Msg) (Screen, tea.Cmd) {
	if key, ok := msg.(tea.KeyMsg); ok {
		switch keyName(key) {
		case "esc", "q", "enter":
			m.app.Pop()
		}
	}
	return m, nil
}

// View renders the panel.
func (m *modal) View() string {
	return panelStyle.Render(strings.Join(m.lines, "\n"))
}

// Hints lists the modal keymap.
func (m *modal) Hints() []Hint { return []Hint{{"esc", "close"}} }

// InitResultScreen shows the outcome of a project initialization.
type InitResultScreen struct {
	modal
	result core.InitResult
}

// NewInitResultScreen builds the initialization summary panel.
func NewInitResultScreen(app *App, result core.InitResult) *InitResultScreen {
	lines := []string{
		"Initialize project structure (.promptcraft) — done, existing templates were not touched.",
		"",
	}
	for _, message := range result.Created {
		lines = append(lines, "  • "+message)
	}
	for _, message := range result.Existing {
		lines = append(lines, "  • "+message)
	}
	screen := &InitResultScreen{modal: modal{app: app, lines: lines}, result: result}
	return screen
}

// Init notifies that the structure is ready.
func (s *InitResultScreen) Init() tea.Cmd {
	s.app.Notify("Project structure ready.", "information")
	return nil
}

// VersionScreen shows the installed version.
type VersionScreen struct {
	modal
}

// NewVersionScreen builds the version panel.
func NewVersionScreen(app *App) *VersionScreen {
	return &VersionScreen{modal: modal{app: app, lines: []string{
		"Installed version",
		"",
		fmt.Sprintf("PromptCraft v%s", version.Version),
	}}}
}

// HelpScreen shows the full keyboard reference.
type HelpScreen struct {
	modal
}

// NewHelpScreen builds the help panel.
func NewHelpScreen(app *App) *HelpScreen {
	return &HelpScreen{modal: modal{app: app, lines: []string{"Keyboard shortcuts", "", HelpText}}}
}
