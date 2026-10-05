// Package cli implements the promptcraft command-line entry point.
package cli

import (
	"errors"
	"fmt"
	"io"
	"strings"

	"github.com/spf13/cobra"

	"github.com/quantmind-br/promptcraft/internal/apperror"
	"github.com/quantmind-br/promptcraft/internal/clipboard"
	"github.com/quantmind-br/promptcraft/internal/core"
	"github.com/quantmind-br/promptcraft/internal/style"
	"github.com/quantmind-br/promptcraft/internal/tui"
	"github.com/quantmind-br/promptcraft/internal/version"
)

// Options carries the dependencies of a run so tests can inject them.
type Options struct {
	Out           io.Writer
	Core          *core.Processor
	Deps          clipboard.Deps
	IsInteractive func() bool
	LaunchTUI     func() error
	Color         bool
}

// Run executes the CLI and returns the process exit code.
func Run(args []string, opts Options) int {
	out := opts.Out
	if out == nil {
		out = io.Discard
	}
	printer := &style.Printer{Enabled: opts.Color}

	if opts.Core == nil {
		opts.Core = core.New()
	}
	if opts.IsInteractive == nil {
		opts.IsInteractive = func() bool { return false }
	}
	if opts.LaunchTUI == nil {
		opts.LaunchTUI = func() error { return tui.Run(opts.Core, opts.Deps, out) }
	}

	var exitCode int

	command := &cobra.Command{
		Use:           "promptcraft [COMMAND_NAME] [ARGUMENTS...]",
		Short:         "PromptCraft CLI - A command-line tool for managing prompt templates",
		Long:          longHelp(),
		Version:       version.Version,
		SilenceUsage:  true,
		SilenceErrors: true,
		Run: func(cmd *cobra.Command, positional []string) {
			flags := cmd.Flags()
			stdoutFlag, _ := flags.GetBool("stdout")
			initFlag, _ := flags.GetBool("init")
			listFlag, _ := flags.GetBool("list")

			if initFlag {
				initializeProject(opts.Core, out, printer)
				exitCode = 0
				return
			}
			if listFlag {
				listCommands(opts.Core, out, printer)
				exitCode = 0
				return
			}
			if len(positional) == 0 {
				if !stdoutFlag && opts.IsInteractive() {
					if err := opts.LaunchTUI(); err != nil {
						writeLine(out, printer.Red("Interactive interface unavailable: "+err.Error()))
						writeLine(out, printer.Red("Run 'promptcraft --help' for command-line usage"))
						exitCode = 1
						return
					}
					exitCode = 0
					return
				}
				writeLine(out, printer.Red("❌ Command name is required"))
				writeLine(out, printer.Red("Use 'promptcraft --help' for usage information"))
				exitCode = 1
				return
			}

			commandName := strings.TrimPrefix(positional[0], "/")
			exitCode = executeCommand(opts.Core, opts.Deps, commandName, positional[1:], stdoutFlag, out, printer)
		},
	}

	command.Flags().Bool("stdout", false, "Output to terminal instead of clipboard")
	command.Flags().Bool("init", false, "Initialize PromptCraft project structure")
	command.Flags().Bool("list", false, "List all available commands")
	command.SetArgs(args)
	command.SetOut(out)
	command.SetErr(out)
	command.SetVersionTemplate(fmt.Sprintf("PromptCraft, version %s\n", version.Version))

	if err := command.Execute(); err != nil {
		writeLine(out, printer.Red("❌ "+err.Error()))
		return 1
	}
	return exitCode
}

func longHelp() string {
	return `PromptCraft CLI - A command-line tool for managing prompt templates.

Execute slash commands to generate prompts quickly and efficiently.

Usage Examples:
    promptcraft /create-story "Epic Story" feature
    promptcraft /fix-bug urgent security
    promptcraft /code-review main.py

Commands are discovered from template files in .promptcraft/commands/
directories, searched in current directory and user home directory.

Generated prompts are automatically copied to your clipboard.
Use --stdout flag to output to terminal instead of clipboard.

COMMAND_NAME: The slash command to execute (with or without leading slash)
ARGUMENTS: Arguments to pass to the command template

Options:
    --stdout    Output to terminal instead of clipboard
`
}

func executeCommand(processor *core.Processor, deps clipboard.Deps, commandName string, arguments []string, stdoutFlag bool, out io.Writer, printer *style.Printer) int {
	result, err := processor.ProcessCommand(commandName, arguments)
	if err != nil {
		var perr *apperror.Error
		if errors.As(err, &perr) && perr.Code() == apperror.CodeCommandNotFound {
			writeLine(out, printer.Red(fmt.Sprintf("❌ Command '/%s' not found", commandName)))
			writeLine(out, printer.Red("Run 'promptcraft --list' to see available commands"))
			return 1
		}
		if errors.As(err, &perr) {
			writeLine(out, printer.Red("❌ "+perr.Message))
			return 1
		}
		writeLine(out, printer.Red("❌ Unexpected error occurred"))
		return 1
	}

	if stdoutFlag {
		writeLine(out, printer.Green(fmt.Sprintf("✅ Prompt for '/%s' generated:", commandName)))
		writeLine(out, result)
		return 0
	}

	route := clipboard.Copy(result, deps)
	if route != "" {
		if route == clipboard.RouteOSC52 {
			// OSC 52 is fire-and-forget: the terminal never confirms the copy.
			writeLine(out, printer.Green(fmt.Sprintf("✅ Prompt for '/%s' sent to clipboard via terminal (OSC 52)!", commandName)))
		} else {
			writeLine(out, printer.Green(fmt.Sprintf("✅ Prompt for '/%s' copied to clipboard!", commandName)))
		}
		return 0
	}

	writeLine(out, printer.Yellow("⚠️ Clipboard unavailable, use --stdout instead"))
	writeLine(out, printer.Green(fmt.Sprintf("✅ Prompt for '/%s' generated:", commandName)))
	writeLine(out, result)
	return 0
}

func initializeProject(processor *core.Processor, out io.Writer, printer *style.Printer) {
	result := processor.InitProject()
	if result.Error != "" {
		if strings.Contains(result.Error, "Permission denied") {
			writeLine(out, printer.Red("❌ Permission denied: Cannot create directories"))
			writeLine(out, printer.Red("Try running with appropriate permissions"))
			return
		}
		writeLine(out, printer.Red("❌ "+result.Error))
		return
	}

	writeLine(out, printer.Green("✅ PromptCraft initialized! Created .promptcraft/commands/ with example template"))
	writeLine(out, "\n📁 Project structure:")
	for _, item := range result.Items {
		writef(out, "  • %s\n", item)
	}

	writeLine(out, "\n👉 Next steps:")
	writeLine(out, "  1. Try the example: promptcraft exemplo 'hello world'")
	writeLine(out, "  2. Edit .promptcraft/commands/exemplo.md to customize")
	writeLine(out, "  3. Create new .md files for your own templates")
	writeLine(out, "  4. Use 'promptcraft --help' for more options")
}

func listCommands(processor *core.Processor, out io.Writer, printer *style.Printer) {
	commands := processor.DiscoverCommands()
	if len(commands) == 0 {
		writeLine(out, printer.Yellow("No commands found"))
		writeLine(out, "Run 'promptcraft --init' to create examples.")
		return
	}

	writeLine(out, printer.Green("Available Commands ("+fmt.Sprint(len(commands))+" found):"))
	writeLine(out, "")

	maxName, maxSource := len("Command"), len("Source")
	for _, command := range commands {
		if len(command.Name) > maxName {
			maxName = len(command.Name)
		}
		if len(command.Source) > maxSource {
			maxSource = len(command.Source)
		}
	}

	header := fmt.Sprintf("%-*s %-*s %s", maxName, "Command", maxSource, "Source", "Description")
	writeLine(out, printer.Cyan(header))
	writeLine(out, printer.Cyan(strings.Repeat("-", len(header))))

	for _, command := range commands {
		paddedSource := fmt.Sprintf("%-*s", maxSource, command.Source)
		if command.Source == core.SourceProject {
			paddedSource = printer.Green(paddedSource)
		} else {
			paddedSource = printer.Blue(paddedSource)
		}
		writef(out, "%-*s %s %s\n", maxName, command.Name, paddedSource, command.Description)
	}
}

// writeLine and writef ignore write errors: the CLI reports prompt text, and a
// failed write means the caller is gone.
func writeLine(out io.Writer, text string) { _, _ = fmt.Fprintln(out, text) }

func writef(out io.Writer, format string, args ...any) { _, _ = fmt.Fprintf(out, format, args...) }
