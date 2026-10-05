// Package style renders coloured terminal output with the same palette the CLI
// has always used. Colour is disabled when the output is not a terminal or when
// NO_COLOR is set, so tests compare plain text.
package style

import (
	"os"

	"github.com/mattn/go-isatty"
)

// Printer renders styled text.
type Printer struct {
	Enabled bool
}

// New returns a printer for the given output file.
func New(out *os.File) Printer {
	enabled := isatty.IsTerminal(out.Fd()) || isatty.IsCygwinTerminal(out.Fd())
	if os.Getenv("NO_COLOR") != "" || os.Getenv("TERM") == "dumb" {
		enabled = false
	}
	return Printer{Enabled: enabled}
}

func (p *Printer) paint(code, text string) string {
	if !p.Enabled {
		return text
	}
	return "\x1b[" + code + "m" + text + "\x1b[0m"
}

// Green renders green text.
func (p *Printer) Green(text string) string { return p.paint("32", text) }

// Red renders red text.
func (p *Printer) Red(text string) string { return p.paint("31", text) }

// Yellow renders yellow text.
func (p *Printer) Yellow(text string) string { return p.paint("33", text) }

// Blue renders blue text.
func (p *Printer) Blue(text string) string { return p.paint("34", text) }

// Cyan renders bold cyan text.
func (p *Printer) Cyan(text string) string { return p.paint("36;1", text) }

// Bold renders bold text.
func (p *Printer) Bold(text string) string { return p.paint("1", text) }
