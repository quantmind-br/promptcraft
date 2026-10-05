// Command promptcraft generates prompts from markdown templates.
package main

import (
	"os"

	"github.com/mattn/go-isatty"

	"github.com/quantmind-br/promptcraft/internal/cli"
	"github.com/quantmind-br/promptcraft/internal/clipboard"
	"github.com/quantmind-br/promptcraft/internal/core"
	"github.com/quantmind-br/promptcraft/internal/style"
)

func main() {
	options := cli.Options{
		Out:   os.Stdout,
		Core:  core.New(),
		Deps:  clipboard.Default(),
		Color: style.New(os.Stdout).Enabled,
		IsInteractive: func() bool {
			return (isatty.IsTerminal(os.Stdin.Fd()) || isatty.IsCygwinTerminal(os.Stdin.Fd())) &&
				(isatty.IsTerminal(os.Stdout.Fd()) || isatty.IsCygwinTerminal(os.Stdout.Fd()))
		},
	}

	os.Exit(cli.Run(os.Args[1:], options))
}
