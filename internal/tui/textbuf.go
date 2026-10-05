package tui

import (
	"strings"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/x/ansi"
)

type bufferState struct {
	text      string
	line, col int
}

// TextBuf is a deterministic multiline editor with bounded undo and cell-aware scrolling.
type TextBuf struct {
	Lines               []string
	CaretLine, CaretCol int
	Focused             bool
	width, height       int
	undo, redo          []bufferState
}

func NewTextBuf(content string, width, height int) TextBuf {
	return TextBuf{Lines: strings.Split(strings.ReplaceAll(content, "\r\n", "\n"), "\n"), width: width, height: height}
}
func (b *TextBuf) Text() string              { return strings.Join(b.Lines, "\n") }
func (b *TextBuf) SetSize(width, height int) { b.width, b.height = max(1, width), max(1, height) }
func (b *TextBuf) ensure() {
	if len(b.Lines) == 0 {
		b.Lines = []string{""}
	}
	b.CaretLine = clamp(b.CaretLine, 0, len(b.Lines)-1)
	b.CaretCol = clamp(b.CaretCol, 0, len([]rune(b.Lines[b.CaretLine])))
}
func (b *TextBuf) InsertRune(r rune) {
	b.ensure()
	runes := []rune(b.Lines[b.CaretLine])
	runes = append(runes[:b.CaretCol], append([]rune{r}, runes[b.CaretCol:]...)...)
	b.Lines[b.CaretLine] = string(runes)
	b.CaretCol++
}
func (b *TextBuf) Backspace() {
	b.ensure()
	if b.CaretCol > 0 {
		runes := []rune(b.Lines[b.CaretLine])
		b.Lines[b.CaretLine] = string(append(runes[:b.CaretCol-1], runes[b.CaretCol:]...))
		b.CaretCol--
	} else if b.CaretLine > 0 {
		previous := b.Lines[b.CaretLine-1]
		b.Lines[b.CaretLine-1] = previous + b.Lines[b.CaretLine]
		b.Lines = append(b.Lines[:b.CaretLine], b.Lines[b.CaretLine+1:]...)
		b.CaretLine--
		b.CaretCol = len([]rune(previous))
	}
}
func (b *TextBuf) deleteForward() {
	b.ensure()
	runes := []rune(b.Lines[b.CaretLine])
	if b.CaretCol < len(runes) {
		b.Lines[b.CaretLine] = string(append(runes[:b.CaretCol], runes[b.CaretCol+1:]...))
	} else if b.CaretLine < len(b.Lines)-1 {
		b.Lines[b.CaretLine] += b.Lines[b.CaretLine+1]
		b.Lines = append(b.Lines[:b.CaretLine+1], b.Lines[b.CaretLine+2:]...)
	}
}
func (b *TextBuf) InsertNewline() {
	b.ensure()
	runes := []rune(b.Lines[b.CaretLine])
	rest := string(runes[b.CaretCol:])
	b.Lines[b.CaretLine] = string(runes[:b.CaretCol])
	b.Lines = append(b.Lines[:b.CaretLine+1], append([]string{rest}, b.Lines[b.CaretLine+1:]...)...)
	b.CaretLine++
	b.CaretCol = 0
}
func (b *TextBuf) MoveCaret(direction string) {
	b.ensure()
	switch direction {
	case "left":
		if b.CaretCol > 0 {
			b.CaretCol--
		} else if b.CaretLine > 0 {
			b.CaretLine--
			b.CaretCol = len([]rune(b.Lines[b.CaretLine]))
		}
	case "right":
		if b.CaretCol < len([]rune(b.Lines[b.CaretLine])) {
			b.CaretCol++
		} else if b.CaretLine < len(b.Lines)-1 {
			b.CaretLine++
			b.CaretCol = 0
		}
	case "up":
		b.CaretLine = max(0, b.CaretLine-1)
	case "down":
		b.CaretLine = min(len(b.Lines)-1, b.CaretLine+1)
	case "home", "ctrl+a":
		b.CaretCol = 0
	case "end", "ctrl+e":
		b.CaretCol = len([]rune(b.Lines[b.CaretLine]))
	case "pgup":
		b.CaretLine = max(0, b.CaretLine-max(1, b.height))
	case "pgdown":
		b.CaretLine = min(len(b.Lines)-1, b.CaretLine+max(1, b.height))
	}
	b.ensure()
}
func (b *TextBuf) snapshot() bufferState { return bufferState{b.Text(), b.CaretLine, b.CaretCol} }
func (b *TextBuf) restore(state bufferState) {
	b.Lines = strings.Split(state.text, "\n")
	b.CaretLine, b.CaretCol = state.line, state.col
	b.ensure()
}
func (b *TextBuf) Update(msg tea.Msg) {
	key, ok := msg.(tea.KeyMsg)
	if !ok || !b.Focused {
		return
	}
	b.ensure()
	before := b.snapshot()
	name := key.String()
	if name == "ctrl+z" {
		if len(b.undo) > 0 {
			b.redo = append(b.redo, before)
			b.restore(b.undo[len(b.undo)-1])
			b.undo = b.undo[:len(b.undo)-1]
		}
		return
	}
	if name == "ctrl+y" {
		if len(b.redo) > 0 {
			b.undo = append(b.undo, before)
			b.restore(b.redo[len(b.redo)-1])
			b.redo = b.redo[:len(b.redo)-1]
		}
		return
	}
	switch key.Type {
	case tea.KeyEnter:
		b.InsertNewline()
	case tea.KeyBackspace, tea.KeyCtrlH:
		b.Backspace()
	case tea.KeyDelete:
		b.deleteForward()
	case tea.KeySpace:
		b.InsertRune(' ')
	case tea.KeyRunes:
		for _, r := range strings.ReplaceAll(string(key.Runes), "\r\n", "\n") {
			switch r {
			case '\n', '\r':
				b.InsertNewline()
			case '\t':
				b.InsertRune(' ')
				b.InsertRune(' ')
				b.InsertRune(' ')
				b.InsertRune(' ')
			default:
				if r >= 32 && r != 127 {
					b.InsertRune(r)
				}
			}
		}
	default:
		b.MoveCaret(name)
	}
	if before.text != b.Text() {
		b.undo = append(b.undo, before)
		if len(b.undo) > 100 {
			b.undo = b.undo[len(b.undo)-100:]
		}
		b.redo = nil
	}
}
func (b *TextBuf) View() string {
	b.ensure()
	if b.height <= 0 {
		return b.Text()
	}
	start := max(0, b.CaretLine-b.height+1)
	end := min(start+b.height, len(b.Lines))
	lines := make([]string, 0, end-start)
	for i := start; i < end; i++ {
		line := b.Lines[i]
		offset := 0
		if i == b.CaretLine {
			runes := []rune(line)
			before := string(runes[:b.CaretCol])
			cursor, after := " ", ""
			if b.CaretCol < len(runes) {
				cursor = string(runes[b.CaretCol])
				after = string(runes[b.CaretCol+1:])
			}
			if b.Focused {
				line = before + caretStyle.Render(cursor) + after
			}
			if b.width > 0 {
				offset = max(0, ansi.StringWidth(before)+max(1, ansi.StringWidth(cursor))-b.width)
			}
		}
		if b.width > 0 {
			line = ansi.Cut(line, offset, offset+b.width)
		}
		lines = append(lines, line)
	}
	return strings.Join(lines, "\n")
}
