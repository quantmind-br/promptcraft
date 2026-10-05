// Package core implements PromptCraft template discovery and processing.
//
// The behaviour mirrors the legacy Python implementation: hierarchical search
// paths (project then user), $ARGUMENTS substitution, first-line description
// extraction, mtime-based caches, and the same error codes.
package core

import (
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/quantmind-br/promptcraft/internal/apperror"
)

// Cache TTLs, identical to the legacy implementation.
const (
	PathCacheTTL      = 5 * time.Second
	DiscoveryCacheTTL = 10 * time.Second
)

// Source labels used by discovery and the CLI table.
const (
	SourceProject = "Project"
	SourceGlobal  = "Global"
)

// CommandInfo describes one discovered command template.
type CommandInfo struct {
	Name        string
	Path        string
	Source      string // "Project" or "Global"
	Description string
}

// Scope returns the scope identifier for a discovered template.
func (c CommandInfo) Scope() string {
	if c.Source == SourceGlobal {
		return ScopeUser
	}
	return ScopeProject
}

type pathEntry struct {
	cachedAt time.Time
	path     string // empty string records a cached miss
}

type discoveryEntry struct {
	cachedAt time.Time
	commands []CommandInfo
}

// Processor resolves templates and keeps the discovery caches. Caches live on
// the instance so callers (CLI, TUI, tests) can work with isolated processors.
type Processor struct {
	Cwd  func() (string, error)
	Home func() (string, error)
	Now  func() time.Time

	pathCache      map[string]pathEntry
	discoveryCache map[string]discoveryEntry
}

// New returns a processor using the process working directory and home.
func New() *Processor {
	return &Processor{
		Cwd:            os.Getwd,
		Home:           os.UserHomeDir,
		Now:            time.Now,
		pathCache:      map[string]pathEntry{},
		discoveryCache: map[string]discoveryEntry{},
	}
}

// InvalidateCaches clears the discovery and path caches. Call it after
// template files change on disk.
// ensureCaches makes the zero value usable: caches are created on first use.
func (p *Processor) ensureCaches() {
	if p.pathCache == nil {
		p.pathCache = map[string]pathEntry{}
	}
	if p.discoveryCache == nil {
		p.discoveryCache = map[string]discoveryEntry{}
	}
	if p.Now == nil {
		p.Now = time.Now
	}
	if p.Cwd == nil {
		p.Cwd = os.Getwd
	}
	if p.Home == nil {
		p.Home = os.UserHomeDir
	}
}

func (p *Processor) InvalidateCaches() {
	p.ensureCaches()
	p.pathCache = map[string]pathEntry{}
	p.discoveryCache = map[string]discoveryEntry{}
}

func (p *Processor) cwdString() string {
	value, err := p.Cwd()
	if err != nil {
		return ""
	}
	return value
}

func (p *Processor) homeString() string {
	value, err := p.Home()
	if err != nil {
		return ""
	}
	return value
}

// ProjectDir is .promptcraft/commands in the working directory.
func (p *Processor) ProjectDir() string {
	return filepath.Join(p.cwdString(), ".promptcraft", "commands")
}

// UserDir is .promptcraft/commands in the user home directory.
func (p *Processor) UserDir() string {
	return filepath.Join(p.homeString(), ".promptcraft", "commands")
}

// ProcessTemplate validates template content and returns it unchanged.
func (p *Processor) ProcessTemplate(content string) (string, error) {
	if strings.TrimSpace(content) == "" {
		return "", apperror.TemplateError("Template content cannot be empty")
	}
	return content, nil
}

// FindCommandPath locates a command template file in the hierarchical search
// paths: project first, then user. Results and misses are cached for PathCacheTTL.
func (p *Processor) FindCommandPath(commandName string) (string, error) {
	p.ensureCaches()
	if commandName == "" {
		return "", apperror.CommandNotFoundError("Command name must be a non-empty string")
	}

	cwd := p.cwdString()
	home := p.homeString()
	key := strings.Join([]string{cwd, home, commandName}, "\x00")

	if entry, ok := p.pathCache[key]; ok {
		if p.Now().Sub(entry.cachedAt) < PathCacheTTL {
			if entry.path == "" {
				return "", apperror.CommandNotFoundError(notFoundMessage(p, commandName))
			}
			if isFile(entry.path) {
				return entry.path, nil
			}
		}
	}

	filename := commandName + ".md"
	searchPaths := []string{
		filepath.Join(cwd, ".promptcraft", "commands", filename),
		filepath.Join(home, ".promptcraft", "commands", filename),
	}

	for _, path := range searchPaths {
		if isFile(path) {
			p.pathCache[key] = pathEntry{cachedAt: p.Now(), path: path}
			return path, nil
		}
	}

	p.pathCache[key] = pathEntry{cachedAt: p.Now(), path: ""}
	return "", apperror.CommandNotFoundError(notFoundMessage(p, commandName))
}

func notFoundMessage(p *Processor, commandName string) string {
	locations := []string{p.ProjectDir(), p.UserDir()}
	return "Command '" + commandName + "' not found. Searched in: " + strings.Join(locations, ", ")
}

func isFile(path string) bool {
	info, err := os.Stat(path)
	if err != nil {
		return false
	}
	return !info.IsDir()
}
