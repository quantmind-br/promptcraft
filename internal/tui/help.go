package tui

import (
	"fmt"
	"io"

	"github.com/charmbracelet/bubbles/list"
	tea "github.com/charmbracelet/bubbletea"

	"github.com/quantmind-br/promptcraft/internal/clipboard"
	"github.com/quantmind-br/promptcraft/internal/core"
)

const HelpText = `LIBRARY
  ↑/↓ or j/k       Select a template
  PgUp/PgDn        Browse pages
  / or Ctrl+F      Search name, description and source
  Enter/r          Open the selected template
  n / e / d        New / edit / delete (confirm twice)
  i / f / v        Project setup / refresh / about
  ?                Open this guide
  q / Esc          Quit (Esc clears search or confirmation first)

RUN A TEMPLATE
  Type             Fill $ARGUMENTS with your text
  Enter/Ctrl+S     Generate and copy
  Ctrl+P           Generate and preview, without copying
  Tab/Shift+Tab    Move between field and actions
  s / d            Copy / preview when the field is not focused
  Esc              Return to the library

GENERATED PROMPT
  ↑/↓, PgUp/PgDn   Scroll (Home/End jump to the edges)
  c                Copy or retry clipboard delivery
  Esc/q            Return to the arguments

TEMPLATE EDITOR
  Tab/Shift+Tab    Next / previous field
  ←/→ or ↑/↓       Change the project/user scope
  Ctrl+S           Save (confirm overwrites twice)
  Ctrl+D           Delete an existing template (confirm twice)
  Esc              Back; repeat Esc to discard unsaved changes
  Ctrl+Q           Quit; repeat to discard unsaved changes
  Home/End         Start / end of the current content line
  Ctrl+Z/Ctrl+Y    Undo / redo content edits

TEMPLATE SYNTAX
  $ARGUMENTS       Full supplied text
  $ARGUMENTS[0]    First CLI argument (indexes start at zero)
  The first line is the description shown in the library.
  Project templates take precedence over user templates.

CLIPBOARD
  Native clipboard when available; OSC 52 through the terminal.
  OSC 52 delivery is sent, not acknowledged by the terminal.
  If copying fails, use Ctrl+P to view and select the result.

GLOBAL
  Ctrl+Q/Ctrl+C    Quit safely (unsaved changes require confirmation)`

func copyFeedback(route, name string, chars int) (string, string) {
	if route == clipboard.RouteOSC52 {
		return fmt.Sprintf("✓ Sent to clipboard via terminal (OSC 52, %d chars).", chars), fmt.Sprintf("/%s sent to clipboard (OSC 52)", name)
	}
	return fmt.Sprintf("✓ Copied to clipboard (%d chars).", chars), fmt.Sprintf("/%s copied to clipboard", name)
}

type templateItem struct{ info core.CommandInfo }

func (i templateItem) FilterValue() string { return i.info.Name + " " + i.info.Description }

type templateDelegate struct{ compact bool }

func (d templateDelegate) Height() int {
	if d.compact {
		return 1
	}
	return 2
}
func (d templateDelegate) Spacing() int {
	if d.compact {
		return 0
	}
	return 1
}
func (d templateDelegate) Update(_ tea.Msg, _ *list.Model) tea.Cmd { return nil }
func (d templateDelegate) Render(w io.Writer, m list.Model, index int, item list.Item) {
	entry, ok := item.(templateItem)
	if !ok {
		return
	}
	width := max(1, m.Width())
	marker, style := "  ", itemStyle
	if index == m.Index() {
		marker, style = "› ", selectedStyle
	}
	name := marker + "/" + entry.info.Name + "  [" + entry.info.Source + "]"
	if d.compact {
		_, _ = fmt.Fprint(w, style.Render(fitLine(name, width)))
		return
	}
	description := entry.info.Description
	if description == "" {
		description = "No description yet"
	}
	_, _ = fmt.Fprint(w, style.Render(fitLine(name, width))+"\n"+dimStyle.Render(fitLine("  "+description, width)))
}
