// Package apperror defines the structured errors used by PromptCraft.
//
// Every error carries a human-readable message and an error code used for
// programmatic handling, mirroring the legacy Python exception hierarchy.
package apperror

// Error codes reported by PromptCraft errors.
const (
	CodeCommandNotFound      = "COMMAND_NOT_FOUND"
	CodeTemplateReadError    = "TEMPLATE_READ_ERROR"
	CodeTemplateFileNotFound = "TEMPLATE_FILE_NOT_FOUND"
	CodeTemplatePermission   = "TEMPLATE_PERMISSION_DENIED"
	CodeTemplateEncoding     = "TEMPLATE_ENCODING_ERROR"
	CodeTemplateIO           = "TEMPLATE_IO_ERROR"
)

// Error is a PromptCraft error with a structured code.
type Error struct {
	Message   string
	ErrorCode string
}

// Error implements the error interface and returns the human-readable message.
func (e *Error) Error() string { return e.Message }

// Code returns the structured error code.
func (e *Error) Code() string { return e.ErrorCode }

// New creates a base PromptCraft error with the given code.
func New(message, code string) *Error {
	return &Error{Message: message, ErrorCode: code}
}

// TemplateError reports a failure while processing template content.
func TemplateError(message string) *Error {
	return New(message, "TEMPLATE_ERROR")
}

// ConfigurationError reports a configuration-related failure.
func ConfigurationError(message string) *Error {
	return New(message, "CONFIGURATION_ERROR")
}

// CommandNotFoundError reports a command template that no search path contains.
func CommandNotFoundError(message string) *Error {
	return New(message, CodeCommandNotFound)
}

// TemplateReadError reports a failure while reading a template file.
func TemplateReadError(message, code string) *Error {
	if code == "" {
		code = CodeTemplateReadError
	}
	return New(message, code)
}
