package tui

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"

	"github.com/quantmind-br/promptcraft/internal/core"
)

// Scope labels used by the editor, matching the CLI labels.
var scopeLabels = map[string]string{
	core.ScopeProject: core.SourceProject,
	core.ScopeUser:    core.SourceGlobal,
}

// scopeOptions is the ordered list shown by the scope selector.
var scopeOptions = []string{core.ScopeProject, core.ScopeUser}

// TemplateScreen creates or edits a template in the chosen scope.
type TemplateScreen struct {
	app             *App
	mode            string // "create" or "edit"
	template        core.CommandInfo
	name            textinput.Model
	scope           int
	content         TextBuf
	focus           string // "name", "scope" or "content"
	status          string
	confirmedTarget string
	confirmedDelete string
}

// NewTemplateScreen builds the editor.
func NewTemplateScreen(app *App, mode string, template core.CommandInfo) *TemplateScreen {
	input := textinput.New()
	input.Prompt = "name: "
	input.Placeholder = "my-command"
	input.Focus()

	screen := &TemplateScreen{
		app:      app,
		mode:     mode,
		template: template,
		name:     input,
		focus:    "name",
	}

	if mode == "edit" {
		screen.name.SetValue(template.Name)
		for index, option := range scopeOptions {
			if option == template.Scope() {
				screen.scope = index
				break
			}
		}
		content, err := app.core.LoadTemplateContent(template.Path)
		if err != nil {
			screen.status = "✗ Could not read " + template.Path + ": " + err.Error()
			screen.app.Notify("Could not read "+template.Path+": "+err.Error(), "error")
			return screen
		}
		screen.content = NewTextBuf(content, max(1, app.width), max(1, app.height-8))
	} else {
		screen.content = NewTextBuf("", max(1, app.width), max(1, app.height-8))
		if defaultScope(app) == core.ScopeUser {
			screen.scope = 1
		}
	}

	return screen
}

func defaultScope(app *App) string {
	if info, err := os.Stat(app.core.ProjectDir()); err == nil && info.IsDir() {
		return core.ScopeProject
	}
	return core.ScopeUser
}

// Init focuses the name field.
func (s *TemplateScreen) Init() tea.Cmd { return nil }

// Update routes keys: Tab cycles focus, Ctrl+S saves, Ctrl+D deletes.
func (s *TemplateScreen) Update(msg tea.Msg) (Screen, tea.Cmd) {
	switch message := msg.(type) {
	case tea.WindowSizeMsg:
		s.name.Width = max(1, message.Width-7)
		s.content.SetSize(max(1, message.Width), max(1, message.Height-8))
		return s, nil
	case tea.KeyMsg:
		name := keyName(message)
		switch name {
		case "ctrl+s":
			s.save()
			return s, nil
		case "ctrl+d":
			s.delete()
			return s, nil
		case "tab":
			s.cycleFocus()
			return s, nil
		case "esc", "q":
			if s.confirmedDelete != "" {
				s.confirmedDelete = ""
				s.status = "Delete cancelled."
				return s, nil
			}
			s.app.Pop()
			return s, nil
		}

		var cmd tea.Cmd
		switch s.focus {
		case "name":
			s.name, cmd = s.name.Update(message)
			if name == "enter" {
				s.save()
			}
		case "scope":
			if name == "up" || name == "down" {
				s.scope = clamp(s.scope+delta(name), 0, len(scopeOptions)-1)
			}
		case "content":
			s.content.Focused = true
			s.content.Update(message)
		}
		return s, cmd
	}
	return s, nil
}

func (s *TemplateScreen) cycleFocus() {
	switch s.focus {
	case "name":
		s.focus = "scope"
		s.name.Blur()
	case "scope":
		s.focus = "content"
		s.content.Focused = true
	default:
		s.focus = "name"
		s.content.Focused = false
		s.name.Focus()
	}
}

// save writes the template, confirming an overwrite on the second Ctrl+S.
func (s *TemplateScreen) save() {
	s.confirmedDelete = ""
	rawName := s.name.Value()
	scope := scopeOptions[s.scope]
	content := s.content.Text()

	if message := core.ValidateName(rawName); message != "" {
		s.status = "✗ " + message
		s.app.Notify(message, "error")
		return
	}
	if strings.TrimSpace(content) == "" {
		message := "Content is required (the first line becomes the description)."
		s.status = "✗ " + message
		s.app.Notify(message, "error")
		return
	}

	normalized := core.NormalizeName(rawName)
	target, err := s.app.core.TemplateFilePath(normalized, scope)
	if err != nil {
		s.status = "✗ " + err.Error()
		s.app.Notify(err.Error(), "error")
		return
	}

	label := scopeLabels[scope]
	isMove := s.mode == "edit" && filepath.Clean(target) != filepath.Clean(s.template.Path)

	if exists(target) {
		sameFile := s.mode == "edit" && !isMove
		if !sameFile && target != s.confirmedTarget {
			s.confirmedTarget = target
			message := fmt.Sprintf("⚠ Template '%s' already exists in the %s scope. Press Ctrl+S again to overwrite it.", normalized, label)
			if s.mode == "edit" {
				origin := fmt.Sprintf("'%s' [%s]", s.template.Name, s.template.Source)
				message = fmt.Sprintf("⚠ Template '%s' already exists in the %s scope and will be overwritten (the original %s will be removed — this is a move). Press Ctrl+S again to confirm.", normalized, label, origin)
			}
			s.status = message
			s.app.Notify(message, "warning")
			return
		}
	}

	path, err := s.app.core.SaveTemplate(normalized, scope, content)
	if err != nil {
		s.status = "✗ Save failed: " + err.Error()
		s.app.Notify("Save failed: "+err.Error(), "error")
		return
	}

	if isMove {
		original := s.template.Path
		if filepath.Clean(original) != filepath.Clean(path) && exists(original) {
			if err := s.app.core.DeleteTemplate(original); err != nil {
				s.app.Notify(fmt.Sprintf("Saved %s to %s scope, but could not remove the original %s: %s", filepath.Base(path), label, original, err.Error()), "warning")
				s.app.Pop()
				return
			}
		}
		s.status = fmt.Sprintf("✓ Moved: %s → %s  (%s scope)", original, path, label)
		s.app.Notify(fmt.Sprintf("Moved %s from %s to %s scope as %s", filepath.Base(original), s.template.Source, label, filepath.Base(path)), "information")
		s.app.Pop()
		return
	}

	s.status = fmt.Sprintf("✓ Saved: %s  (%s scope)", path, label)
	s.app.Notify(fmt.Sprintf("Saved %s to %s scope", filepath.Base(path), label), "information")
	s.app.Pop()
}

// delete removes the template being edited, confirming on the second Ctrl+D.
func (s *TemplateScreen) delete() {
	if s.mode != "edit" {
		message := "Cannot delete an unsaved template."
		s.status = "✗ " + message
		s.app.Notify(message, "warning")
		return
	}

	pathKey := s.template.Path
	if pathKey != s.confirmedDelete {
		s.confirmedDelete = pathKey
		message := fmt.Sprintf("⚠ Delete '/%s' [%s]? Press Ctrl+D again to confirm.", s.template.Name, s.template.Source)
		s.status = message
		s.app.Notify(message, "warning")
		return
	}

	s.confirmedDelete = ""
	if err := s.app.core.DeleteTemplate(pathKey); err != nil {
		if errors.Is(err, os.ErrNotExist) {
			s.app.Notify(fmt.Sprintf("/%s was already deleted.", s.template.Name), "warning")
			s.app.Pop()
			return
		}
		s.status = "✗ Delete failed: " + err.Error()
		s.app.Notify("Delete failed: "+err.Error(), "error")
		return
	}

	s.app.Notify(fmt.Sprintf("Deleted /%s [%s]", s.template.Name, s.template.Source), "information")
	s.app.Pop()
}

func exists(path string) bool {
	info, err := os.Stat(path)
	return err == nil && !info.IsDir()
}

func clamp(value, low, high int) int {
	if value < low {
		return low
	}
	if value > high {
		return high
	}
	return value
}

func delta(direction string) int {
	if direction == "up" {
		return -1
	}
	return 1
}

// View renders the editor.
func (s *TemplateScreen) View() string {
	title := "New template"
	if s.mode == "edit" {
		title = fmt.Sprintf("Editing template: /%s  ·  [%s]", s.template.Name, s.template.Source)
	}

	scopeView := ""
	for index, option := range scopeOptions {
		marker := "  "
		if index == s.scope {
			marker = "> "
		}
		label := "Project — .promptcraft/commands (this project)"
		if option == core.ScopeUser {
			label = "User — ~/.promptcraft/commands (all projects)"
		}
		line := marker + label
		if index == s.scope && s.focus == "scope" {
			line = selectedStyle.Render(line)
		}
		scopeView += line + "\n"
	}

	hint := "The first line of the content is shown as the description in the list. Use $ARGUMENTS where the typed arguments go. Save with Ctrl+S."

	return fmt.Sprintf("%s\n%s\n%s\n%s\n%s", title, s.name.View(), scopeView, s.content.View(), statusStyle.Render(s.status)+"\n"+dimStyle.Render(hint))
}

// Hints lists the editor keymap.
func (s *TemplateScreen) Hints() []Hint {
	hints := []Hint{{"tab", "field"}, {"ctrl+s", "save"}}
	if s.mode == "edit" {
		hints = append(hints, Hint{"ctrl+d", "delete"})
	}
	return append(hints, Hint{"esc", "back (discard)"})
}
