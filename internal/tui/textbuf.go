package tui

import (
	"strings"

	tea "github.com/charmbracelet/bubbletea"
)

// TextBuf is a small multiline text buffer used by the template editor. It is
// kept in this package instead of a third-party widget so the editing state is
// deterministic and testable.
type TextBuf struct {
	Lines     []string
	CaretLine int
	CaretCol  int
	Focused   bool

	width  int
	height int
}

// NewTextBuf creates a buffer for the given content and geometry.
func NewTextBuf(content string, width, height int) TextBuf {
	lines := strings.Split(content, "\n")
	if len(lines) == 0 {
		lines = []string{""}
	}
	return TextBuf{Lines: lines, width: width, height: height}
}

// Text returns the buffer content.
func (b *TextBuf) Text() string { return strings.Join(b.Lines, "\n") }

// SetSize updates the geometry used for rendering and scrolling.
func (b *TextBuf) SetSize(width, height int) {
	if width > 0 {
		b.width = width
	}
	if height > 0 {
		b.height = height
	}
}

// InsertRune writes a printable rune at the caret.
func (b *TextBuf) InsertRune(r rune) {
	line := b.Lines[b.CaretLine]
	runes := []rune(line)
	runes = append(runes[:b.CaretCol], append([]rune{r}, runes[b.CaretCol:]...)...)
	b.Lines[b.CaretLine] = string(runes)
	b.CaretCol++
}

// Backspace removes the character before the caret.
func (b *TextBuf) Backspace() {
	if b.CaretCol > 0 {
		line := []rune(b.Lines[b.CaretLine])
		line = append(line[:b.CaretCol-1], line[b.CaretCol:]...)
		b.Lines[b.CaretLine] = string(line)
		b.CaretCol--
		return
	}
	if b.CaretLine == 0 {
		return
	}
	previous := b.Lines[b.CaretLine-1]
	b.Lines[b.CaretLine-1] = previous + b.Lines[b.CaretLine]
	b.Lines = append(b.Lines[:b.CaretLine], b.Lines[b.CaretLine+1:]...)
	b.CaretLine--
	b.CaretCol = len([]rune(previous))
}

// InsertNewline splits the current line at the caret.
func (b *TextBuf) InsertNewline() {
	line := []rune(b.Lines[b.CaretLine])
	rest := string(line[b.CaretCol:])
	b.Lines[b.CaretLine] = string(line[:b.CaretCol])
	b.Lines = append(b.Lines[:b.CaretLine+1], append([]string{rest}, b.Lines[b.CaretLine+1:]...)...)
	b.CaretLine++
	b.CaretCol = 0
}

// MoveCaret handles arrow navigation inside the buffer.
func (b *TextBuf) MoveCaret(direction string) {
	runes := []rune(b.Lines[b.CaretLine])
	switch direction {
	case "left":
		if b.CaretCol > 0 {
			b.CaretCol--
		} else if b.CaretLine > 0 {
			b.CaretLine--
			b.CaretCol = len([]rune(b.Lines[b.CaretLine]))
		}
	case "right":
		if b.CaretCol < len(runes) {
			b.CaretCol++
		} else if b.CaretLine < len(b.Lines)-1 {
			b.CaretLine++
			b.CaretCol = 0
		}
	case "up":
		if b.CaretLine > 0 {
			b.CaretLine--
			if b.CaretCol > len([]rune(b.Lines[b.CaretLine])) {
				b.CaretCol = len([]rune(b.Lines[b.CaretLine]))
			}
		}
	case "down":
		if b.CaretLine < len(b.Lines)-1 {
			b.CaretLine++
			if b.CaretCol > len([]rune(b.Lines[b.CaretLine])) {
				b.CaretCol = len([]rune(b.Lines[b.CaretLine]))
			}
		}
	}
}

// Update forwards a key message to the buffer when it has focus.
func (b *TextBuf) Update(msg tea.Msg) {
	key, ok := msg.(tea.KeyMsg)
	if !ok || !b.Focused {
		return
	}

	switch key.Type {
	case tea.KeyEnter:
		b.InsertNewline()
	case tea.KeyBackspace, tea.KeyCtrlH:
		b.Backspace()
	case tea.KeySpace:
		b.InsertRune(' ')
	case tea.KeyRunes:
		if len(key.Runes) > 0 {
			for _, r := range key.Runes {
				b.InsertRune(r)
			}
		}
	case tea.KeyLeft, tea.KeyRight, tea.KeyUp, tea.KeyDown:
		b.MoveCaret(strings.ToLower(key.String()))
	}
}

// View renders the visible window of the buffer.
// View renders the visible window of the buffer, wrapping to its width and
// marking the caret position when the buffer has focus.
func (b *TextBuf) View() string {
	if b.height <= 0 {
		return strings.Join(b.Lines, "\n")
	}

	start := 0
	if b.CaretLine >= b.height {
		start = b.CaretLine - b.height + 1
	}
	end := min(start+b.height, len(b.Lines))

	rendered := make([]string, 0, end-start)
	for index := start; index < end; index++ {
		runes := []rune(b.Lines[index])
		startCol := 0
		if b.width > 0 && len(runes) > b.width {
			if index == b.CaretLine {
				startCol = max(0, min(len(runes)-b.width, b.CaretCol-b.width+1))
			} else {
				startCol = 0
			}
		}
		stop := min(startCol+b.width, len(runes))
		if b.width <= 0 {
			stop = len(runes)
		}

		visible := runes[startCol:stop]
		if b.Focused && index == b.CaretLine && startCol <= b.CaretCol && b.CaretCol < stop {
			parts := make([]string, 0, len(visible))
			for offset, r := range visible {
				text := string(r)
				if startCol+offset == b.CaretCol {
					text = caretStyle.Render(text)
				}
				parts = append(parts, text)
			}
			rendered = append(rendered, strings.Join(parts, ""))
			continue
		}
		rendered = append(rendered, string(visible))
	}

	return strings.Join(rendered, "\n")
}
