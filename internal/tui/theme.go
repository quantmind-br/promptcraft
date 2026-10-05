package tui

import (
	"strings"

	"github.com/charmbracelet/lipgloss"
	"github.com/charmbracelet/x/ansi"
)

// Adaptive colors keep the hierarchy legible on both light and dark terminals.
var (
	accent    = lipgloss.AdaptiveColor{Light: "#6441B8", Dark: "#B49AFF"}
	muted     = lipgloss.AdaptiveColor{Light: "#657080", Dark: "#929AAF"}
	border    = lipgloss.AdaptiveColor{Light: "#CDD2DF", Dark: "#41485D"}
	textColor = lipgloss.AdaptiveColor{Light: "#252A38", Dark: "#E3E7F0"}
	selection = lipgloss.AdaptiveColor{Light: "#EDE6FF", Dark: "#322B49"}

	headerStyle   = lipgloss.NewStyle().Bold(true).Foreground(accent)
	statusStyle   = lipgloss.NewStyle().Foreground(textColor)
	dimStyle      = lipgloss.NewStyle().Foreground(muted)
	errorStyle    = lipgloss.NewStyle().Foreground(lipgloss.AdaptiveColor{Light: "#B42332", Dark: "#FF8996"})
	warnStyle     = lipgloss.NewStyle().Foreground(lipgloss.AdaptiveColor{Light: "#926100", Dark: "#F5CF83"})
	infoStyle     = lipgloss.NewStyle().Foreground(lipgloss.AdaptiveColor{Light: "#167558", Dark: "#8BD5B2"})
	panelStyle    = lipgloss.NewStyle().Border(lipgloss.RoundedBorder()).BorderForeground(border).Padding(0, 1)
	keyStyle      = lipgloss.NewStyle().Bold(true).Foreground(accent)
	caretStyle    = lipgloss.NewStyle().Reverse(true)
	selectedStyle = lipgloss.NewStyle().Bold(true).Foreground(accent).Background(selection)
	itemStyle     = lipgloss.NewStyle().Foreground(textColor)
)

func toastStyle(severity string) lipgloss.Style {
	switch severity {
	case "error":
		return errorStyle
	case "warning":
		return warnStyle
	default:
		return infoStyle
	}
}

// fitLine truncates by terminal cells, not bytes or runes, preserving ANSI styles.
func fitLine(text string, width int) string {
	return ansi.Truncate(strings.ReplaceAll(text, "\n", " "), max(1, width), "…")
}

func wrapText(text string, width int) string {
	return ansi.Wrap(text, max(1, width), "")
}

// fitBlock is a final geometry guard; individual widgets own their scrolling.
func fitBlock(text string, width, height int) string {
	lines := strings.Split(text, "\n")
	result := make([]string, max(1, height))
	for i := range result {
		if i < len(lines) {
			result[i] = fitLine(lines[i], width)
		}
		result[i] += strings.Repeat(" ", max(0, width-ansi.StringWidth(result[i])))
	}
	return strings.Join(result, "\n")
}

func pane(title, content string, width, height int, focused bool) string {
	style := panelStyle
	if focused {
		style = style.BorderForeground(accent)
	}
	innerWidth := max(1, width-4)
	heading := headerStyle.Render(fitLine(title, innerWidth))
	return style.Render(fitBlock(heading+"\n"+content, innerWidth, max(1, height-2)))
}

// hintRows prioritizes escape/help on narrow terminals rather than clipping them away.
func hintRows(hints []Hint, width int) string {
	ordered := make([]Hint, 0, len(hints))
	for _, hint := range hints {
		if hint.Key == "esc" || hint.Key == "q" || hint.Key == "?" {
			ordered = append(ordered, hint)
		}
	}
	for _, hint := range hints {
		if hint.Key != "esc" && hint.Key != "q" && hint.Key != "?" {
			ordered = append(ordered, hint)
		}
	}
	rows := []string{""}
	for _, hint := range ordered {
		entry := keyStyle.Render(hint.Key) + " " + dimStyle.Render(hint.Label)
		last := len(rows) - 1
		separator := ""
		if rows[last] != "" {
			separator = " · "
		}
		if ansi.StringWidth(rows[last]+separator+entry) > width {
			if last == 1 {
				break
			}
			rows = append(rows, entry)
		} else {
			rows[last] += separator + entry
		}
	}
	return fitBlock(strings.Join(rows, "\n"), width, 2)
}
