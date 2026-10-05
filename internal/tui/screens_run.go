package tui

import (
	"errors"
	"strings"

	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/quantmind-br/promptcraft/internal/apperror"
	"github.com/quantmind-br/promptcraft/internal/clipboard"
	"github.com/quantmind-br/promptcraft/internal/core"
)

// RunScreen keeps typing separate from keyboard-selectable actions.
type RunScreen struct {
	app                          *App
	template                     core.CommandInfo
	input                        textinput.Model
	status, result, copiedResult string
	copied                       bool
	action                       int
}

func NewRunScreen(app *App, template core.CommandInfo) *RunScreen {
	input := textinput.New()
	input.Prompt = "› "
	input.Placeholder = "Type the arguments, or leave empty"
	input.TextStyle = headerStyle
	input.Focus()
	input.Width = max(1, app.bodyWidth()-7)
	return &RunScreen{app: app, template: template, input: input}
}

func (s *RunScreen) Init() tea.Cmd { return nil }
func (s *RunScreen) Update(msg tea.Msg) (Screen, tea.Cmd) {
	switch message := msg.(type) {
	case tea.WindowSizeMsg:
		s.input.Width = max(1, s.app.bodyWidth()-7)
		return s, nil
	case tea.KeyMsg:
		name := keyName(message)
		switch name {
		case "esc":
			s.app.Pop()
			return s, nil
		case "ctrl+p":
			s.actionDisplay()
			return s, nil
		case "ctrl+s":
			s.actionCopy()
			return s, nil
		case "tab", "shift+tab":
			if s.input.Focused() {
				s.input.Blur()
				if name == "shift+tab" {
					s.action = 1
				} else {
					s.action = 0
				}
			} else if (name == "tab" && s.action == 0) || (name == "shift+tab" && s.action == 1) {
				s.action = 1 - s.action
			} else {
				return s, s.input.Focus()
			}
			return s, nil
		}
		if s.input.Focused() {
			var cmd tea.Cmd
			s.input, cmd = s.input.Update(message)
			if name == "enter" {
				s.actionCopy()
			}
			return s, cmd
		}
		switch name {
		case "left", "right", "up", "down":
			s.action = 1 - s.action
		case "enter":
			if s.action == 0 {
				s.actionCopy()
			} else {
				s.actionDisplay()
			}
		case "s":
			s.actionCopy()
		case "d":
			s.actionDisplay()
		case "q":
			s.app.Pop()
		}
	}
	return s, nil
}

// The interactive form treats the full text as one argument; CLI indexes remain available.
func (s *RunScreen) run() (string, error) {
	arguments := []string{}
	if text := trimSpaces(s.input.Value()); text != "" {
		arguments = []string{text}
	}
	result, err := s.app.core.ProcessCommand(s.template.Name, arguments)
	if err != nil {
		var perr *apperror.Error
		message := err.Error()
		if errors.As(err, &perr) {
			message = perr.Message
		}
		s.status = "✗ " + message
		s.app.Notify(message, "error")
		return "", err
	}
	s.result = result
	return result, nil
}

func (s *RunScreen) actionCopy() {
	result, err := s.run()
	if err != nil {
		return
	}
	route := clipboard.Copy(result, s.app.deps)
	if route == "" {
		s.status = "✗ Could not copy to the clipboard. Use Ctrl+P to preview and select the text."
		s.app.Notify("Clipboard unavailable · Ctrl+P opens the result", "error")
		return
	}
	s.copiedResult, s.copied = result, true
	status, toast := copyFeedback(route, s.template.Name, len([]rune(result)))
	s.status = status + " Ctrl+P previews it; Esc returns."
	s.app.Notify(toast, "information")
}

func (s *RunScreen) actionDisplay() {
	result, err := s.run()
	if err == nil {
		s.app.Push(NewResultScreen(s.app, s.template.Name, result, s.copied && result == s.copiedResult))
	}
}

func (s *RunScreen) View() string {
	width, height := s.app.bodyWidth(), s.app.bodyHeight()
	inner := max(1, width-4)
	intro := headerStyle.Render("/"+s.template.Name) + "  " + dimStyle.Render("["+s.template.Source+"]") + "\n" + fitLine(s.description(), inner)
	input := statusStyle.Render(fitLine(s.input.View(), inner))
	copyButton, previewButton := "  Generate & copy  ", "  Preview only  "
	if !s.input.Focused() {
		if s.action == 0 {
			copyButton = selectedStyle.Render(copyButton)
		} else {
			previewButton = selectedStyle.Render(previewButton)
		}
	}
	actions := copyButton + "  " + previewButton
	if lipgloss.Width(actions) > inner {
		actions = copyButton + "\n" + previewButton
	}
	instructions := "Your text replaces $ARGUMENTS. Enter copies; Ctrl+P previews without copying."
	content := intro + "\n\n" + headerStyle.Render("Arguments") + "\n" + input + "\n" + actions + "\n" + dimStyle.Render(wrapText(instructions, inner))
	if s.status != "" {
		content += "\n\n" + statusStyle.Render(wrapText(s.status, inner))
	}
	if height < 12 {
		content = headerStyle.Render(fitLine("/"+s.template.Name+" · Arguments", width)) + "\n" + input + "\n" + actions
		if height >= 8 {
			content += "\n" + fitLine(s.description(), width)
		}
		return content + "\n" + fitLine(s.status, width)
	}
	return pane("Generate a prompt", content, width, height, true)
}

func (s *RunScreen) description() string {
	if s.template.Description == "" {
		return "No description available"
	}
	return s.template.Description
}
func (s *RunScreen) Hints() []Hint {
	return []Hint{{"enter", "generate & copy"}, {"ctrl+p", "preview"}, {"tab", "next field/action"}, {"shift+tab", "previous"}, {"esc", "back"}}
}
func trimSpaces(text string) string { return strings.TrimSpace(text) }
