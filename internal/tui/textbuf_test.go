package tui

import (
	"strings"
	"testing"

	tea "github.com/charmbracelet/bubbletea"
)

func keyMsg(r rune) tea.KeyMsg { return tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{r}} }

func TestTextBufEditing(t *testing.T) {
	buf := NewTextBuf("", 20, 5)
	buf.Focused = true

	for _, r := range "ab" {
		buf.Update(keyMsg(r))
	}
	if buf.Text() != "ab" {
		t.Fatalf("insert failed: %q", buf.Text())
	}

	buf.Update(tea.KeyMsg{Type: tea.KeySpace})
	buf.Update(keyMsg('c'))
	if buf.Text() != "ab c" {
		t.Fatalf("space must be inserted as a character: %q", buf.Text())
	}

	buf.Update(tea.KeyMsg{Type: tea.KeyEnter})
	buf.Update(keyMsg('d'))
	if buf.Text() != "ab c\nd" {
		t.Fatalf("newline split failed: %q", buf.Text())
	}

	// Backspace removes the character, then merges the lines at column zero.
	buf.Update(tea.KeyMsg{Type: tea.KeyBackspace})
	if buf.Text() != "ab c\n" || buf.CaretCol != 0 {
		t.Fatalf("backspace failed: %q (col %d)", buf.Text(), buf.CaretCol)
	}
	buf.Update(tea.KeyMsg{Type: tea.KeyBackspace})
	if buf.Text() != "ab c" || buf.CaretLine != 0 {
		t.Fatalf("line merge failed: %q (line %d)", buf.Text(), buf.CaretLine)
	}

	// Keys are ignored while the buffer has no focus.
	buf.Focused = false
	buf.Update(keyMsg('x'))
	if buf.Text() != "ab c" {
		t.Fatalf("unfocused buffer must ignore keys: %q", buf.Text())
	}
}

func TestTextBufCaretMovement(t *testing.T) {
	buf := NewTextBuf("one\ntwo", 20, 3)
	buf.Focused = true
	buf.CaretLine = 1
	buf.CaretCol = 0

	buf.Update(tea.KeyMsg{Type: tea.KeyUp})
	if buf.CaretLine != 0 || buf.CaretCol != 0 {
		t.Fatalf("up keeps the column when the previous line is longer: %d/%d", buf.CaretLine, buf.CaretCol)
	}

	buf.Update(tea.KeyMsg{Type: tea.KeyRight})
	buf.Update(tea.KeyMsg{Type: tea.KeyRight})
	buf.Update(tea.KeyMsg{Type: tea.KeyRight})
	buf.Update(tea.KeyMsg{Type: tea.KeyRight})
	if buf.CaretLine != 1 || buf.CaretCol != 0 {
		t.Fatalf("right must wrap to the next line: %d/%d", buf.CaretLine, buf.CaretCol)
	}

	buf.Update(tea.KeyMsg{Type: tea.KeyDown})
	if buf.CaretLine != 1 {
		t.Fatalf("down from the last line must stay put: %d", buf.CaretLine)
	}

	buf.Update(tea.KeyMsg{Type: tea.KeyLeft})
	if buf.CaretLine != 0 || buf.CaretCol != 3 {
		t.Fatalf("left must wrap to the previous line: %d/%d", buf.CaretLine, buf.CaretCol)
	}
}

func TestTextBufScrollsTheVisibleWindow(t *testing.T) {
	buf := NewTextBuf(strings.Repeat("line\n", 10), 20, 4)
	buf.CaretLine = 8
	window := strings.Split(buf.View(), "\n")
	if len(window) != 4 || window[0] != "line" {
		t.Fatalf("window must show the caret line: %v", window)
	}

	if got := buf.Text(); got != strings.Repeat("line\n", 10) {
		t.Fatalf("text reconstruction failed: %q", got)
	}
}
