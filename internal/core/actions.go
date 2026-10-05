package core

import (
	_ "embed"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"strings"
)

// Scope identifiers used by the TUI.
const (
	ScopeProject = "project"
	ScopeUser    = "user"
)

// ExampleTemplate is the template written by --init and the TUI init action.
//
//go:embed example_template.md
var ExampleTemplate string

// InitResult is the outcome of an idempotent project initialization.
type InitResult struct {
	Created  []string
	Existing []string
	Items    []string // messages in the order they were produced
	Error    string
}

// add records a message in the order it was produced and in its category.
func (r *InitResult) add(message string, created bool) {
	r.Items = append(r.Items, message)
	if created {
		r.Created = append(r.Created, message)
	} else {
		r.Existing = append(r.Existing, message)
	}
}

// ScopeDir returns the .promptcraft/commands directory for a scope.
func (p *Processor) ScopeDir(scope string) string {
	if scope == ScopeUser {
		return p.UserDir()
	}
	return p.ProjectDir()
}

// NormalizeName turns a user-supplied template name into a file stem: a
// trailing .md typed in the TUI is stripped so the saved file keeps the CLI
// convention.
func NormalizeName(name string) string {
	name = strings.TrimSpace(name)
	if strings.HasSuffix(strings.ToLower(name), ".md") {
		name = strings.TrimSuffix(name, name[len(name)-3:])
	}
	return strings.TrimSpace(name)
}

// ValidateName checks a normalized template name and returns an error message,
// or an empty string when the name is valid.
func ValidateName(name string) string {
	normalized := NormalizeName(name)
	if normalized == "" {
		return "Name is required."
	}
	if strings.Contains(normalized, "/") || strings.Contains(normalized, "\\") {
		return "Name cannot contain path separators ('/' or '\\'). Use a single word or use hyphens."
	}
	if strings.HasPrefix(normalized, ".") {
		return "Name cannot start with a dot."
	}
	return ""
}

// TemplateFilePath returns the path a template name would have in a scope,
// without writing anything.
func (p *Processor) TemplateFilePath(name string, scope string) (string, error) {
	normalized := NormalizeName(name)
	if normalized == "" {
		return "", errors.New("Name is required.") //nolint:staticcheck // user-facing wording must match the legacy CLI
	}
	return filepath.Join(p.ScopeDir(scope), normalized+".md"), nil
}

// SaveTemplate writes a template file in the chosen scope and invalidates the
// caches so discovery and path lookups see the change immediately.
func (p *Processor) SaveTemplate(name string, scope string, content string) (string, error) {
	normalized := NormalizeName(name)
	if message := ValidateName(normalized); message != "" {
		return "", errors.New(message)
	}
	if scope != ScopeProject && scope != ScopeUser {
		return "", fmt.Errorf("Unknown scope: %s", scope) //nolint:staticcheck // user-facing wording must match the legacy CLI
	}

	commandsDir := p.ScopeDir(scope)
	if err := os.MkdirAll(commandsDir, 0o755); err != nil {
		return "", err
	}

	path := filepath.Join(commandsDir, normalized+".md")
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		return "", err
	}

	p.InvalidateCaches()
	return path, nil
}

// LoadTemplateContent reads a template file.
func (p *Processor) LoadTemplateContent(path string) (string, error) {
	content, err := os.ReadFile(path)
	if err != nil {
		return "", err
	}
	return string(content), nil
}

// DeleteTemplate removes a template file from one of the two known template
// directories. Anything outside them is refused.
func (p *Processor) DeleteTemplate(path string) error {
	resolved, err := filepath.Abs(path)
	if err != nil {
		return err
	}
	resolved = filepath.Clean(resolved)

	allowed := []string{}
	for _, base := range []string{p.ProjectDir(), p.UserDir()} {
		clean, err := filepath.Abs(base)
		if err != nil {
			continue
		}
		allowed = append(allowed, filepath.Clean(clean))
	}

	inside := false
	for _, base := range allowed {
		if resolved != base && strings.HasPrefix(resolved, base+string(os.PathSeparator)) {
			inside = true
			break
		}
	}
	if !inside {
		return fmt.Errorf("Refusing to delete outside template directories: %s", path) //nolint:staticcheck // user-facing wording must match the legacy CLI
	}

	info, err := os.Stat(resolved)
	if err != nil {
		if errors.Is(err, fs.ErrNotExist) {
			return fs.ErrNotExist
		}
		return err
	}
	if info.IsDir() {
		return fmt.Errorf("Cannot delete directory: %s", path) //nolint:staticcheck // user-facing wording must match the legacy CLI
	}

	if err := os.Remove(resolved); err != nil {
		return err
	}

	p.InvalidateCaches()
	return nil
}

// InitProject idempotently initializes the project structure in the current
// directory. Existing templates are never overwritten.
func (p *Processor) InitProject() InitResult {
	result := InitResult{}
	commandsDir := filepath.Join(p.cwdString(), ".promptcraft", "commands")

	dirExisted := false
	if info, err := os.Stat(commandsDir); err == nil && info.IsDir() {
		dirExisted = true
	}

	if err := os.MkdirAll(commandsDir, 0o755); err != nil {
		if errors.Is(err, fs.ErrPermission) {
			result.Error = "Permission denied: cannot create the project structure. Try running in a directory you can write to."
			return result
		}
		result.Error = fmt.Sprintf("Error creating project structure: %v", err)
		return result
	}

	if dirExisted {
		result.add("Directory already exists: .promptcraft/commands/", false)
	} else {
		result.add("Created directory: .promptcraft/commands/", true)
	}

	exampleFile := filepath.Join(commandsDir, "exemplo.md")
	if _, err := os.Stat(exampleFile); err == nil {
		result.add("Example template already exists: exemplo.md", false)
	} else {
		if err := os.WriteFile(exampleFile, []byte(ExampleTemplate), 0o644); err != nil {
			result.Error = fmt.Sprintf("Error creating project structure: %v", err)
			return result
		}
		result.add("Created example template: exemplo.md", true)
	}

	return result
}
