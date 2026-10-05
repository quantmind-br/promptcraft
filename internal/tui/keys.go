package tui

import (
	"strings"

	tea "github.com/charmbracelet/bubbletea"
)

// keyName normalises a key message for dispatch: printable runes are compared
// case-insensitively, special keys keep their name ("enter", "esc", "ctrl+s").
func keyName(msg tea.KeyMsg) string {
	name := msg.String()
	if len(name) == 1 {
		return strings.ToLower(name)
	}
	return name
}
