package tui

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"

	"github.com/quantmind-br/promptcraft/internal/clipboard"
)

// ResultScreen presents wrapped text without modifying what is copied.
type ResultScreen struct {
	app                   *App
	name, content, status string
	copied                bool
	viewport              viewport.Model
}

func NewResultScreen(app *App, name, content string, copied bool) *ResultScreen {
	screen := &ResultScreen{app: app, name: name, content: content, copied: copied, viewport: viewport.New(1, 1)}
	screen.status = "Clipboard was not used for this result. Press c to copy it."
	if copied {
		screen.status = "✓ Already copied to the clipboard. Press c to copy again."
	}
	screen.resize()
	return screen
}
func (s *ResultScreen) Init() tea.Cmd { return nil }
func (s *ResultScreen) resize() {
	offset := s.viewport.YOffset
	s.viewport.Width = max(1, s.app.bodyWidth()-4)
	s.viewport.Height = max(1, s.resultHeight())
	s.viewport.SetContent(wrapText(s.content, s.viewport.Width))
	s.viewport.SetYOffset(offset)
}
func (s *ResultScreen) Update(msg tea.Msg) (Screen, tea.Cmd) {
	switch message := msg.(type) {
	case tea.WindowSizeMsg:
		s.resize()
		return s, nil
	case tea.KeyMsg:
		switch keyName(message) {
		case "c", "ctrl+s":
			route := clipboard.Copy(s.content, s.app.deps)
			if route == "" {
				s.status = "✗ Could not copy to the clipboard. Select the text, or use --stdout."
				s.app.Notify("Clipboard copy failed · the preview remains available", "error")
				return s, nil
			}
			s.copied = true
			status, toast := copyFeedback(route, s.name, len([]rune(s.content)))
			s.status = status
			s.app.Notify(toast, "information")
			return s, nil
		case "esc", "q":
			s.app.Pop()
			return s, nil
		case "home":
			s.viewport.GotoTop()
			return s, nil
		case "end":
			s.viewport.GotoBottom()
			return s, nil
		}
	}
	var cmd tea.Cmd
	s.viewport, cmd = s.viewport.Update(msg)
	return s, cmd
}
func (s *ResultScreen) resultHeight() int {
	if s.app.bodyHeight() < 8 {
		return max(1, s.app.bodyHeight()-3)
	}
	return max(1, s.app.bodyHeight()-5)
}

func (s *ResultScreen) View() string {
	width := s.app.bodyWidth()
	title := fmt.Sprintf("/%s · %d characters · %d lines", s.name, len([]rune(s.content)), strings.Count(s.content, "\n")+1)
	progress := dimStyle.Render(fmt.Sprintf("Scroll %3.0f%% · ↑/↓ or PgUp/PgDn", s.viewport.ScrollPercent()*100))
	if s.app.bodyHeight() < 8 {
		return headerStyle.Render(fitLine(title, width)) + "\n" + s.viewport.View() + "\n" + progress + "\n" + fitLine(s.status, width)
	}
	return pane(title, s.viewport.View(), width, s.app.bodyHeight()-2, true) + "\n" + progress + "\n" + fitLine(statusStyle.Render(s.status), width)
}
func (s *ResultScreen) Hints() []Hint {
	return []Hint{{"↑/↓", "scroll"}, {"pgup/pgdn", "page"}, {"home/end", "jump"}, {"c", "copy"}, {"esc", "back"}}
}
