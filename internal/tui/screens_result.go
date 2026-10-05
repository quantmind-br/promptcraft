package tui

import (
	"fmt"

	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"

	"github.com/quantmind-br/promptcraft/internal/clipboard"
)

// ResultScreen shows a generated prompt read-only with a copy action.
type ResultScreen struct {
	app      *App
	name     string
	content  string
	copied   bool
	status   string
	viewport viewport.Model
}

// NewResultScreen builds the result view.
func NewResultScreen(app *App, name, content string, copied bool) *ResultScreen {
	view := viewport.New(max(1, app.width), max(1, app.height-5))
	view.SetContent(content)

	status := "Clipboard was not used for this result. Press c to copy it."
	if copied {
		status = "✓ Already copied to the clipboard. Press c to copy again."
	}

	return &ResultScreen{app: app, name: name, content: content, copied: copied, status: status, viewport: view}
}

// Init prepares the viewport.
func (s *ResultScreen) Init() tea.Cmd { return nil }

// Update handles scrolling and the copy/back shortcuts.
func (s *ResultScreen) Update(msg tea.Msg) (Screen, tea.Cmd) {
	switch message := msg.(type) {
	case tea.WindowSizeMsg:
		s.viewport.Width = max(1, message.Width)
		s.viewport.Height = max(1, message.Height-5)
		return s, nil
	case tea.KeyMsg:
		switch keyName(message) {
		case "c":
			route := clipboard.Copy(s.content, s.app.deps)
			if route == "" {
				s.status = "✗ Could not copy to the clipboard. The text is shown here — select it with your terminal, or use --stdout on the CLI."
				s.app.Notify("Clipboard copy failed", "error")
				return s, nil
			}
			status, toast := copyFeedback(route, s.name, len([]rune(s.content)))
			s.status = status
			s.app.Notify(toast, "information")
			return s, nil
		case "esc", "q":
			s.app.Pop()
			return s, nil
		}

		var cmd tea.Cmd
		s.viewport, cmd = s.viewport.Update(message)
		return s, cmd
	}
	return s, nil
}

// View renders the title, the content and the status line.
func (s *ResultScreen) View() string {
	title := fmt.Sprintf("Result for /%s  ·  %d chars", s.name, len([]rune(s.content)))
	return fmt.Sprintf("%s\n%s\n%s", title, s.viewport.View(), statusStyle.Render(s.status))
}

// Hints lists the result keymap.
func (s *ResultScreen) Hints() []Hint {
	return []Hint{{"c", "copy to clipboard"}, {"esc", "back"}}
}
