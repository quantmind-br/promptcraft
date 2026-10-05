package tui

import (
	"errors"
	"fmt"
	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
	"strings"

	"github.com/quantmind-br/promptcraft/internal/apperror"
	"github.com/quantmind-br/promptcraft/internal/clipboard"
	"github.com/quantmind-br/promptcraft/internal/core"
)

// RunScreen fills a template's arguments and runs it (clipboard or on screen).
type RunScreen struct {
	app          *App
	template     core.CommandInfo
	input        textinput.Model
	status       string
	result       string
	copiedResult string
}

// NewRunScreen builds the run form for a template.
func NewRunScreen(app *App, template core.CommandInfo) *RunScreen {
	input := textinput.New()
	input.Prompt = "args: "
	input.Placeholder = fmt.Sprintf("Arguments for /%s (space-separated, leave empty if none)", template.Name)
	input.Focus()
	return &RunScreen{app: app, template: template, input: input}
}

// Init focuses the arguments field.
func (s *RunScreen) Init() tea.Cmd { return nil }

// Update routes keys: while the field has focus typing goes to it, Tab leaves it
// so the shortcuts below work.
func (s *RunScreen) Update(msg tea.Msg) (Screen, tea.Cmd) {
	switch message := msg.(type) {
	case tea.WindowSizeMsg:
		s.input.Width = max(1, message.Width-7)
		return s, nil
	case tea.KeyMsg:
		name := keyName(message)
		// Escape and quit have priority over the field, as in the legacy bindings.
		if name == "esc" || name == "q" {
			s.app.Pop()
			return s, nil
		}

		if s.input.Focused() && name != "tab" {
			var cmd tea.Cmd
			s.input, cmd = s.input.Update(message)
			if name == "enter" {
				s.actionCopy()
			}
			return s, cmd
		}

		switch keyName(message) {
		case "tab":
			s.input.Blur() // leave the field so the shortcuts below work
			return s, nil
		case "s", "enter":
			s.actionCopy()
			return s, nil
		case "d":
			s.actionDisplay()
			return s, nil
		case "esc", "q":
			s.app.Pop()
			return s, nil
		}
	}
	return s, nil
}

// run processes the template with the typed arguments. The whole line is one
// argument, matching the legacy behaviour.
func (s *RunScreen) run() (string, error) {
	raw := s.input.Value()
	arguments := []string{}
	if trimmed := trimSpaces(raw); trimmed != "" {
		arguments = []string{trimmed}
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

// actionCopy runs the template and sends the result to the clipboard.
func (s *RunScreen) actionCopy() {
	result, err := s.run()
	if err != nil {
		return
	}
	route := clipboard.Copy(result, s.app.deps)
	if route == "" {
		s.status = "✗ Could not copy to the clipboard. Press d to view the text on screen (CLI equivalent: use --stdout)."
		s.app.Notify("Clipboard copy failed", "error")
		return
	}
	s.copiedResult = result
	status, toast := copyFeedback(route, s.template.Name, len([]rune(result)))
	s.status = status + " Press d to view it on screen, Esc to go back."
	s.app.Notify(toast, "information")
}

// actionDisplay runs the template and shows the result on screen.
func (s *RunScreen) actionDisplay() {
	result, err := s.run()
	if err != nil {
		return
	}
	copied := result == s.copiedResult
	s.app.Push(NewResultScreen(s.app, s.template.Name, result, copied))
}

// View renders the title, the arguments field, the hint and the status.
func (s *RunScreen) View() string {
	title := fmt.Sprintf("Run: /%s  ·  [%s]  ·  %s", s.template.Name, s.template.Source, s.description())
	hint := "The $ARGUMENTS placeholder is replaced by the arguments you type here. Press Enter to run (copies to the clipboard by default); Tab leaves the field so s and d work."
	return fmt.Sprintf("%s\n%s\n%s\n%s", title, s.input.View(), dimStyle.Render(hint), statusStyle.Render(s.status))
}

func (s *RunScreen) description() string {
	if s.template.Description == "" {
		return "No description available"
	}
	return s.template.Description
}

// Hints lists the run keymap.
func (s *RunScreen) Hints() []Hint {
	return []Hint{{"type", "arguments"}, {"enter", "run + copy"}, {"tab", "leave field"}, {"s", "copy"}, {"d", "show"}, {"esc", "back"}}
}

func trimSpaces(text string) string {
	return strings.TrimSpace(text)
}
