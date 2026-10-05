package core

import (
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
	"unicode/utf8"
)

// DiscoverCommands lists every command template in the two search paths, with
// results cached until a search directory changes or the cache TTL expires.
func (p *Processor) DiscoverCommands() []CommandInfo {
	p.ensureCaches()
	key := p.cwdString() + "\x00" + p.homeString()
	searchPaths := []struct {
		dir    string
		source string
	}{
		{p.ProjectDir(), SourceProject},
		{p.UserDir(), SourceGlobal},
	}

	modTimes := make([]time.Time, 0, len(searchPaths))
	for _, entry := range searchPaths {
		info, err := os.Stat(entry.dir)
		if err != nil || !info.IsDir() {
			modTimes = append(modTimes, time.Time{})
			continue
		}
		modTimes = append(modTimes, info.ModTime())
	}

	if cached, ok := p.discoveryCache[key]; ok {
		newest := time.Time{}
		for _, modTime := range modTimes {
			if modTime.After(newest) {
				newest = modTime
			}
		}
		if !cached.cachedAt.Before(newest) && p.Now().Sub(cached.cachedAt) < DiscoveryCacheTTL {
			return cached.commands
		}
	}

	commands := []CommandInfo{}
	for _, entry := range searchPaths {
		info, err := os.Stat(entry.dir)
		if err != nil || !info.IsDir() {
			continue
		}
		items, err := os.ReadDir(entry.dir)
		if err != nil {
			continue
		}
		for _, item := range items {
			if item.IsDir() || !strings.HasSuffix(item.Name(), ".md") {
				continue
			}
			path := filepath.Join(entry.dir, item.Name())
			commands = append(commands, CommandInfo{
				Name:        strings.TrimSuffix(item.Name(), ".md"),
				Path:        path,
				Source:      entry.source,
				Description: ExtractDescription(path),
			})
		}
	}

	sort.SliceStable(commands, func(i, j int) bool {
		return strings.ToLower(commands[i].Name) < strings.ToLower(commands[j].Name)
	})

	p.discoveryCache[key] = discoveryEntry{cachedAt: p.Now(), commands: commands}
	return commands
}

// ListTemplates returns the templates shown in the TUI list. When the same name
// exists in both scopes the project template wins, matching the precedence the
// CLI applies when resolving a command by name.
func (p *Processor) ListTemplates() []CommandInfo {
	byName := map[string]CommandInfo{}
	for _, command := range p.DiscoverCommands() {
		current, ok := byName[command.Name]
		if !ok || (current.Source != SourceProject && command.Source == SourceProject) {
			byName[command.Name] = command
		}
	}

	templates := make([]CommandInfo, 0, len(byName))
	for _, command := range byName {
		templates = append(templates, command)
	}
	sort.SliceStable(templates, func(i, j int) bool {
		return strings.ToLower(templates[i].Name) < strings.ToLower(templates[j].Name)
	})
	return templates
}

// ExtractDescription returns the first meaningful line of a template file with
// markdown headers cleaned.
func ExtractDescription(path string) string {
	const fallback = "No description available"

	content, err := os.ReadFile(path)
	if err != nil {
		return fallback
	}
	if !utf8.Valid(content) {
		return fallback
	}

	for _, rawLine := range strings.Split(string(content), "\n") {
		firstLine := strings.TrimSpace(rawLine)
		if firstLine == "" {
			continue
		}
		if strings.HasPrefix(firstLine, "#") {
			// Seven or more hashes are not a header: only the first one is removed.
			if strings.HasPrefix(firstLine, "####### ") {
				return strings.TrimSpace(firstLine[1:])
			}
			start := 0
			for start < len(firstLine) && start < 6 && firstLine[start] == '#' {
				start++
			}
			if start < len(firstLine) && firstLine[start] == ' ' {
				start++
			}
			cleaned := strings.TrimSpace(firstLine[start:])
			if cleaned != "" {
				return cleaned
			}
			return fallback
		}
		return firstLine
	}

	return fallback
}
