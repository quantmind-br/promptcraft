package core

import (
	"errors"
	"fmt"
	"io/fs"
	"os"
	"regexp"
	"strings"
	"unicode/utf8"

	"github.com/quantmind-br/promptcraft/internal/apperror"
)

var indexedArgPattern = regexp.MustCompile(`\$ARGUMENTS\[(\d+)\]`)

// GeneratePrompt reads a template file and substitutes the argument
// placeholders. Indexed placeholders ($ARGUMENTS[0]) are resolved before the
// generic one, exactly like the legacy implementation.
func (p *Processor) GeneratePrompt(templatePath string, arguments []string) (string, error) {
	content, err := os.ReadFile(templatePath)
	if err != nil {
		return "", readError(templatePath, err)
	}

	text := string(content)
	if strings.IndexByte(text, 0) >= 0 {
		return "", apperror.TemplateReadError(
			fmt.Sprintf("Failed to decode template file %s: binary content detected", templatePath),
			apperror.CodeTemplateEncoding,
		)
	}
	if !utf8.ValidString(text) {
		return "", apperror.TemplateReadError(
			fmt.Sprintf("Failed to decode template file %s: invalid UTF-8 at position %d", templatePath, firstInvalidUTF8(text)),
			apperror.CodeTemplateEncoding,
		)
	}

	argumentsString := ""
	if len(arguments) > 0 {
		argumentsString = strings.Join(arguments, " ")
	}

	processed := indexedArgPattern.ReplaceAllStringFunc(text, func(match string) string {
		groups := indexedArgPattern.FindStringSubmatch(match)
		if len(groups) < 2 {
			return match
		}
		index := 0
		_, _ = fmt.Sscanf(groups[1], "%d", &index)
		if index < len(arguments) {
			return arguments[index]
		}
		return ""
	})

	return strings.ReplaceAll(processed, "$ARGUMENTS", argumentsString), nil
}

// ProcessCommand resolves the template for a command name and generates the
// final prompt. Errors carry the command name as context.
func (p *Processor) ProcessCommand(commandName string, arguments []string) (string, error) {
	templatePath, err := p.FindCommandPath(commandName)
	if err != nil {
		var perr *apperror.Error
		if errors.As(err, &perr) && perr.Code() == apperror.CodeCommandNotFound {
			return "", apperror.CommandNotFoundError(
				fmt.Sprintf("Command '%s' processing failed: %s", commandName, perr.Message),
			)
		}
		return "", err
	}

	prompt, err := p.GeneratePrompt(templatePath, arguments)
	if err != nil {
		var perr *apperror.Error
		if errors.As(err, &perr) {
			return "", apperror.TemplateReadError(
				fmt.Sprintf("Command '%s' template processing failed: %s", commandName, perr.Message),
				perr.Code(),
			)
		}
		return "", err
	}
	return prompt, nil
}

func readError(templatePath string, err error) error {
	switch {
	case errors.Is(err, fs.ErrNotExist):
		return apperror.TemplateReadError(
			fmt.Sprintf("Template file not found: %s", templatePath),
			apperror.CodeTemplateFileNotFound,
		)
	case errors.Is(err, fs.ErrPermission):
		return apperror.TemplateReadError(
			fmt.Sprintf("Permission denied reading template file: %s", templatePath),
			apperror.CodeTemplatePermission,
		)
	default:
		return apperror.TemplateReadError(
			fmt.Sprintf("I/O error reading template file %s: %v", templatePath, err),
			apperror.CodeTemplateIO,
		)
	}
}

func firstInvalidUTF8(text string) int {
	for i, r := range text {
		if r == utf8.RuneError {
			return i
		}
	}
	return -1
}
