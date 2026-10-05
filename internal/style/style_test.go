package style

import (
	"os"
	"testing"
)

func TestPrinterWritesPlainTextWhenColourIsOff(t *testing.T) {
	printer := Printer{Enabled: false}
	for name, render := range map[string]func(string) string{
		"green":  printer.Green,
		"red":    printer.Red,
		"yellow": printer.Yellow,
		"blue":   printer.Blue,
		"cyan":   printer.Cyan,
		"bold":   printer.Bold,
	} {
		if got := render("text"); got != "text" {
			t.Fatalf("%s must not add escape codes: %q", name, got)
		}
	}
}

func TestPrinterAddsColourCodesWhenEnabled(t *testing.T) {
	printer := Printer{Enabled: true}
	if got := printer.Green("text"); got != "\x1b[32mtext\x1b[0m" {
		t.Fatalf("unexpected green: %q", got)
	}
	if got := printer.Cyan("text"); got != "\x1b[36;1mtext\x1b[0m" {
		t.Fatalf("unexpected cyan: %q", got)
	}
}

func TestNewDisablesColourForNonTerminals(t *testing.T) {
	if printer := New(os.Stdout); printer.Enabled {
		t.Fatal("a captured test output is not a terminal")
	}
}
