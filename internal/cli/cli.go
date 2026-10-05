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

// out aggregates writes and remembers the first failure, so a broken pipe is not
// reported as a successful run.
type out struct {
	writer  io.Writer
	printer *style.Printer
	err     error
}

func (o *out) line(text string) {
	if o.err != nil {
		return
	}
	if _, err := fmt.Fprintln(o.writer, text); err != nil {
		o.err = err
	}
}

func (o *out) printf(format string, args ...any) {
	if o.err != nil {
		return
	}
	if _, err := fmt.Fprintf(o.writer, format, args...); err != nil {
		o.err = err
	}
}

// Run executes the CLI and returns the process exit code.
func Run(args []string, opts Options) int {
	writer := opts.Out
	if writer == nil {
		writer = io.Discard
	}
	printer := &style.Printer{Enabled: opts.Color}
	output := &out{writer: writer, printer: printer}

	if opts.Core == nil {
		opts.Core = core.New()
	}
	if opts.IsInteractive == nil {
		opts.IsInteractive = func() bool { return false }
	}
	if opts.LaunchTUI == nil {
		opts.LaunchTUI = func() error { return tui.Run(opts.Core, opts.Deps, writer) }
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
				exitCode = initializeProject(opts.Core, output)
				return
			}
			if listFlag {
				listCommands(opts.Core, output)
				exitCode = exitForWriteError(output)
				return
			}
			if len(positional) == 0 {
				if !stdoutFlag && opts.IsInteractive() {
					if err := opts.LaunchTUI(); err != nil {
						output.line(output.printer.Red("Interactive interface unavailable: " + err.Error()))
						output.line(output.printer.Red("Run 'promptcraft --help' for command-line usage"))
						exitCode = 1
						return
					}
					exitCode = exitForWriteError(output)
					return
				}
				output.line(output.printer.Red("❌ Command name is required"))
				output.line(output.printer.Red("Use 'promptcraft --help' for usage information"))
				exitCode = 1
				return
			}

			commandName := strings.TrimPrefix(positional[0], "/")
			exitCode = executeCommand(opts.Core, opts.Deps, commandName, positional[1:], stdoutFlag, output)
		},
	}

	command.Flags().Bool("stdout", false, "Output to terminal instead of clipboard")
	command.Flags().Bool("init", false, "Initialize PromptCraft project structure")
	command.Flags().Bool("list", false, "List all available commands")
	command.SetArgs(args)
	command.SetOut(writer)
	command.SetErr(writer)
	command.SetVersionTemplate(fmt.Sprintf("PromptCraft, version %s\n", version.Version))

	if err := command.Execute(); err != nil {
		output.line(output.printer.Red("❌ " + err.Error()))
		return 1
	}
	return exitCode
}

// exitForWriteError keeps a successful path at 0 and reports delivery failures.
func exitForWriteError(output *out) int {
	if output.err != nil {
		return 1
	}
	return 0
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

func executeCommand(processor *core.Processor, deps clipboard.Deps, commandName string, arguments []string, stdoutFlag bool, output *out) int {
	result, err := processor.ProcessCommand(commandName, arguments)
	if err != nil {
		var perr *apperror.Error
		if errors.As(err, &perr) && perr.Code() == apperror.CodeCommandNotFound {
			output.line(output.printer.Red(fmt.Sprintf("❌ Command '/%s' not found", commandName)))
			output.line(output.printer.Red("Run 'promptcraft --list' to see available commands"))
			return 1
		}
		if errors.As(err, &perr) {
			output.line(output.printer.Red("❌ " + perr.Message))
			return 1
		}
		output.line(output.printer.Red("❌ Unexpected error occurred"))
		return 1
	}

	if stdoutFlag {
		output.line(output.printer.Green(fmt.Sprintf("✅ Prompt for '/%s' generated:", commandName)))
		output.line(result)
		return exitForWriteError(output)
	}

	route := clipboard.Copy(result, deps)
	if route != "" {
		if route == clipboard.RouteOSC52 {
			// OSC 52 is fire-and-forget: the terminal never confirms the copy.
			output.line(output.printer.Green(fmt.Sprintf("✅ Prompt for '/%s' sent to clipboard via terminal (OSC 52)!", commandName)))
		} else {
			output.line(output.printer.Green(fmt.Sprintf("✅ Prompt for '/%s' copied to clipboard!", commandName)))
		}
		return exitForWriteError(output)
	}

	output.line(output.printer.Yellow("⚠️ Clipboard unavailable, use --stdout instead"))
	output.line(output.printer.Green(fmt.Sprintf("✅ Prompt for '/%s' generated:", commandName)))
	output.line(result)
	return exitForWriteError(output)
}

func initializeProject(processor *core.Processor, output *out) int {
	result := processor.InitProject()
	if result.Error != "" {
		if strings.Contains(result.Error, "Permission denied") {
			output.line(output.printer.Red("❌ Permission denied: Cannot create directories"))
			output.line(output.printer.Red("Try running with appropriate permissions"))
			return 1
		}
		output.line(output.printer.Red("❌ " + result.Error))
		return 1
	}

	output.line(output.printer.Green("✅ PromptCraft initialized! Created .promptcraft/commands/ with example template"))
	output.line("\n📁 Project structure:")
	for _, item := range result.Items {
		output.printf("  • %s\n", item)
	}

	output.line("\n👉 Next steps:")
	output.line("  1. Try the example: promptcraft exemplo 'hello world'")
	output.line("  2. Edit .promptcraft/commands/exemplo.md to customize")
	output.line("  3. Create new .md files for your own templates")
	output.line("  4. Use 'promptcraft --help' for more options")

	return exitForWriteError(output)
}

func listCommands(processor *core.Processor, output *out) {
	commands := processor.DiscoverCommands()
	if len(commands) == 0 {
		output.line(output.printer.Yellow("No commands found"))
		output.line("Run 'promptcraft --init' to create examples.")
		return
	}

	output.line(output.printer.Green("Available Commands (" + fmt.Sprint(len(commands)) + " found):"))
	output.line("")

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
	output.line(output.printer.Cyan(header))
	output.line(output.printer.Cyan(strings.Repeat("-", len(header))))

	for _, command := range commands {
		paddedSource := fmt.Sprintf("%-*s", maxSource, command.Source)
		if command.Source == core.SourceProject {
			paddedSource = output.printer.Green(paddedSource)
		} else {
			paddedSource = output.printer.Blue(paddedSource)
		}
		output.printf("%-*s %s %s\n", maxName, command.Name, paddedSource, command.Description)
	}
}
