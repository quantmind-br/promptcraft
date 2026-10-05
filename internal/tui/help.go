package tui

import (
	"fmt"
	"io"

	"github.com/charmbracelet/bubbles/list"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/quantmind-br/promptcraft/internal/clipboard"
	"github.com/quantmind-br/promptcraft/internal/core"
)

// HelpText is the full keyboard reference shown by the help panel.
const HelpText = `PromptCraft TUI — keyboard shortcuts
────────────────────────────────────
Home (template list)
  Up / Down        Move through templates
  Enter / r        Run the selected template
  n                Create a new template
  e                Edit the selected template
  d                Delete the selected template (press twice to confirm)
  i                Initialize project structure (.promptcraft)
  v                Show the installed version
  f                Refresh the template list
  ?                Show this help
  q / Esc          Quit

Run template
  Type             Arguments for the $ARGUMENTS placeholder
  Enter            Run and copy the result to the clipboard
  Tab              Leave the field so the shortcuts below work
  s                Run and copy to the clipboard
  d                Run and show the result on screen
  Esc / q          Back (no copy)

Result
  c                Copy the result to the clipboard
  Esc / q          Back

New / edit template
  Tab              Move between name, scope and content
  Ctrl+S           Save the template (project or user scope)
                   Editing to another name/scope moves the template there
                   (the original file is removed).
  Ctrl+D           Delete the template being edited (press twice to confirm)
  Esc / q          Back (discard changes)

Init / version / help
  Esc / q          Close
`

// copyFeedback builds the status line and toast for a successful copy. OSC 52
// writes are never acknowledged by the terminal, so they are reported as sent.
func copyFeedback(route, name string, chars int) (string, string) {
	if route == clipboard.RouteOSC52 {
		return fmt.Sprintf("✓ Sent to clipboard via terminal (OSC 52, %d chars).", chars),
			fmt.Sprintf("/%s sent to clipboard (OSC 52)", name)
	}
	return fmt.Sprintf("✓ Copied to clipboard (%d chars).", chars),
		fmt.Sprintf("/%s copied to clipboard", name)
}

// templateItem wraps a discovered template for the list widget.
type templateItem struct {
	info core.CommandInfo
}

func (i templateItem) FilterValue() string { return i.info.Name }

// templateDelegate renders one row of the template list.
type templateDelegate struct{}

func (d templateDelegate) Height() int                               { return 1 }
func (d templateDelegate) Spacing() int                              { return 0 }
func (d templateDelegate) Update(msg tea.Msg, m *list.Model) tea.Cmd { return nil }

func (d templateDelegate) Render(w io.Writer, m list.Model, index int, item list.Item) {
	entry, ok := item.(templateItem)
	if !ok {
		return
	}
	text := fmt.Sprintf("%s  ·  %s  [%s]", entry.info.Name, entry.info.Description, entry.info.Source)
	if index == m.Index() {
		_, _ = fmt.Fprintln(w, selectedStyle.Render(text))
		return
	}
	_, _ = fmt.Fprintln(w, itemStyle.Render(text))
}

var (
	selectedStyle = lipgloss.NewStyle().Bold(true)
	itemStyle     = lipgloss.NewStyle()
)
