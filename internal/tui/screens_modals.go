package tui

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"

	"github.com/quantmind-br/promptcraft/internal/core"
	"github.com/quantmind-br/promptcraft/internal/version"
)

// modal is a scrollable information panel, never taller than the workspace.
type modal struct {
	app      *App
	title    string
	lines    []string
	viewport viewport.Model
}

func newModal(app *App, title string, lines []string) modal {
	panel := modal{app: app, title: title, lines: lines, viewport: viewport.New(1, 1)}
	panel.resize()
	return panel
}
func (m *modal) resize() {
	offset := m.viewport.YOffset
	m.viewport.Width = max(1, m.app.bodyWidth()-4)
	m.viewport.Height = max(1, m.contentHeight())
	m.viewport.SetContent(wrapText(strings.Join(m.lines, "\n"), m.viewport.Width))
	m.viewport.SetYOffset(offset)
}
func (m *modal) Init() tea.Cmd { return nil }
func (m *modal) Update(msg tea.Msg) (Screen, tea.Cmd) {
	if _, ok := msg.(tea.WindowSizeMsg); ok {
		m.resize()
		return m, nil
	}
	if key, ok := msg.(tea.KeyMsg); ok {
		switch keyName(key) {
		case "esc", "q", "enter":
			m.app.Pop()
			return m, nil
		case "home":
			m.viewport.GotoTop()
			return m, nil
		case "end":
			m.viewport.GotoBottom()
			return m, nil
		}
	}
	var cmd tea.Cmd
	m.viewport, cmd = m.viewport.Update(msg)
	return m, cmd
}
func (m *modal) contentHeight() int {
	if m.app.bodyHeight() < 8 {
		return max(1, m.app.bodyHeight()-2)
	}
	return max(1, m.app.bodyHeight()-4)
}

func (m *modal) View() string {
	if m.app.bodyHeight() < 8 {
		return headerStyle.Render(m.title) + "\n" + m.viewport.View() + "\n" + dimStyle.Render(fmt.Sprintf("Scroll %3.0f%%", m.viewport.ScrollPercent()*100))
	}
	return pane(m.title, m.viewport.View(), m.app.bodyWidth(), m.app.bodyHeight()-1, false) + "\n" + dimStyle.Render(fmt.Sprintf("Scroll %3.0f%%", m.viewport.ScrollPercent()*100))
}
func (m *modal) Hints() []Hint {
	return []Hint{{"↑/↓", "scroll"}, {"pgup/pgdn", "page"}, {"esc", "close"}}
}

type InitResultScreen struct {
	modal
	result core.InitResult
}

func NewInitResultScreen(app *App, result core.InitResult) *InitResultScreen {
	lines := []string{"Project structure ready.", "Existing templates were not touched.", ""}
	for _, message := range result.Items {
		lines = append(lines, "• "+message)
	}
	return &InitResultScreen{modal: newModal(app, "Project setup", lines), result: result}
}
func (s *InitResultScreen) Init() tea.Cmd {
	s.app.Notify("Project structure ready.", "information")
	return nil
}

// Preserve the concrete screen type while using the shared panel behavior.
func (s *InitResultScreen) Update(msg tea.Msg) (Screen, tea.Cmd) {
	_, cmd := s.modal.Update(msg)
	return s, cmd
}

type VersionScreen struct{ modal }

func NewVersionScreen(app *App) *VersionScreen {
	return &VersionScreen{modal: newModal(app, "About PromptCraft", []string{
		fmt.Sprintf("PromptCraft v%s", version.Version), "", "Reusable prompts. Less repetition. More focus.", "",
		"A standalone Go application powered by Bubble Tea.", "Project and user templates · native and terminal clipboard", "", "github.com/quantmind-br/promptcraft",
	})}
}
func (s *VersionScreen) Update(msg tea.Msg) (Screen, tea.Cmd) {
	_, cmd := s.modal.Update(msg)
	return s, cmd
}

type HelpScreen struct{ modal }

func NewHelpScreen(app *App) *HelpScreen {
	return &HelpScreen{modal: newModal(app, "Keyboard guide", []string{HelpText})}
}
func (s *HelpScreen) Update(msg tea.Msg) (Screen, tea.Cmd) {
	_, cmd := s.modal.Update(msg)
	return s, cmd
}
