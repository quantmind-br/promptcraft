package tui

import (
	"errors"
	"fmt"
	"io/fs"
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
	app                         *App
	mode                        string // "create" or "edit"
	template                    core.CommandInfo
	name                        textinput.Model
	scope                       int
	content                     TextBuf
	focus                       string // "name", "scope" or "content"
	status                      string
	confirmedTarget             string
	confirmedDelete             string
	readOnly                    bool
	initialName, initialContent string
	initialScope                int
	discardPending, quitPending bool
}

// NewTemplateScreen builds the editor.
func NewTemplateScreen(app *App, mode string, template core.CommandInfo) *TemplateScreen {
	input := textinput.New()
	input.Prompt = "Name  / "
	input.Placeholder = "my-command"
	input.Focus()

	screen := &TemplateScreen{
		app:      app,
		mode:     mode,
		template: template,
		name:     input,
		focus:    "name",
	}

	screen.content = NewTextBuf("", max(1, app.bodyWidth()-4), max(1, app.bodyHeight()-8))

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
			// The buffer stays empty and read-only so typing cannot corrupt it.
			screen.readOnly = true
			screen.status = "✗ Could not read " + template.Path + ": " + err.Error()
			screen.app.Notify("Could not read "+template.Path+": "+err.Error(), "error")
			return screen
		}
		screen.content = NewTextBuf(content, max(1, app.bodyWidth()-4), max(1, app.bodyHeight()-8))
	} else if defaultScope(app) == core.ScopeUser {
		screen.scope = 1
	}

	screen.initialName, screen.initialContent = screen.name.Value(), screen.content.Text()
	screen.initialScope = screen.scope
	screen.resize()
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

// Update routes input without stealing printable keys from text fields.
func (s *TemplateScreen) Update(msg tea.Msg) (Screen, tea.Cmd) {
	if _, ok := msg.(tea.WindowSizeMsg); ok {
		s.resize()
		return s, nil
	}
	message, ok := msg.(tea.KeyMsg)
	if !ok {
		return s, nil
	}
	name := keyName(message)
	switch name {
	case "ctrl+s":
		s.save()
		return s, nil
	case "ctrl+d":
		s.delete()
		return s, nil
	case "tab", "shift+tab":
		s.discardPending, s.quitPending = false, false
		direction := 1
		if name == "shift+tab" {
			direction = -1
		}
		return s, s.changeFocus(direction)
	case "esc":
		return s, s.back()
	case "q":
		if s.focus == "scope" {
			return s, s.back()
		}
	}
	before := s.name.Value() + "\x00" + s.content.Text()
	oldScope := s.scope
	var cmd tea.Cmd
	switch s.focus {
	case "name":
		s.name, cmd = s.name.Update(message)
		if name == "enter" {
			return s, s.changeFocus(1)
		}
	case "scope":
		if name == "up" || name == "left" {
			s.scope = max(0, s.scope-1)
		}
		if name == "down" || name == "right" {
			s.scope = min(len(scopeOptions)-1, s.scope+1)
		}
	case "content":
		if !s.readOnly {
			s.content.Update(message)
		}
	}
	if before != s.name.Value()+"\x00"+s.content.Text() || oldScope != s.scope {
		s.confirmedTarget, s.confirmedDelete = "", ""
		s.discardPending, s.quitPending = false, false
		s.status = ""
	}
	return s, cmd
}

func (s *TemplateScreen) resize() {
	s.name.Width = max(1, s.app.bodyWidth()-12)
	s.content.SetSize(max(1, s.app.bodyWidth()-4), max(1, s.app.bodyHeight()-8))
}
func (s *TemplateScreen) changeFocus(direction int) tea.Cmd {
	fields := []string{"name", "scope", "content"}
	index := 0
	for i, field := range fields {
		if field == s.focus {
			index = i
		}
	}
	s.focus = fields[(index+direction+len(fields))%len(fields)]
	s.name.Blur()
	s.content.Focused = s.focus == "content" && !s.readOnly
	if s.focus == "name" {
		return s.name.Focus()
	}
	return nil
}
func (s *TemplateScreen) dirty() bool {
	return !s.readOnly && (s.name.Value() != s.initialName || s.scope != s.initialScope || s.content.Text() != s.initialContent)
}
func (s *TemplateScreen) requestQuit() tea.Cmd {
	if s.quitPending {
		s.app.Quit()
		return tea.Quit
	}
	s.quitPending = true
	s.status = "Unsaved changes. Press Ctrl+Q again to discard and quit; Ctrl+S saves."
	s.app.Notify(s.status, "warning")
	return nil
}
func (s *TemplateScreen) back() tea.Cmd {
	if s.confirmedDelete != "" || s.confirmedTarget != "" || s.quitPending {
		s.confirmedDelete, s.confirmedTarget = "", ""
		s.quitPending = false
		s.status = "Confirmation cancelled."
		return nil
	}
	if s.dirty() && !s.discardPending {
		s.discardPending = true
		s.status = "Unsaved changes. Press Esc again to discard; Ctrl+S saves."
		s.app.Notify(s.status, "warning")
		return nil
	}
	s.app.Pop()
	return nil
}

// save writes the template, confirming an overwrite on the second Ctrl+S.
func (s *TemplateScreen) save() {
	s.discardPending, s.quitPending = false, false
	if s.readOnly {
		message := "Cannot save a template whose content could not be read."
		s.status = "✗ " + message
		s.app.Notify(message, "error")
		return
	}
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

	targetExists, statErr := statFile(target)
	if statErr != nil {
		s.status = "✗ Save failed: " + statErr.Error()
		s.app.Notify(statErr.Error(), "error")
		return
	}
	if targetExists {
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
		if originalExists, statErr := statFile(original); statErr == nil && originalExists && filepath.Clean(original) != filepath.Clean(path) {
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

// statFile reports whether the path exists as a file. An unexpected stat failure
// is returned as an error instead of being read as absence.
func statFile(path string) (bool, error) {
	info, err := os.Stat(path)
	if err != nil {
		if errors.Is(err, fs.ErrNotExist) {
			return false, nil
		}
		return false, err
	}
	return !info.IsDir(), nil
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

// View renders metadata, a bounded content pane and persistent save feedback.
func (s *TemplateScreen) View() string {
	width, height := s.app.bodyWidth(), s.app.bodyHeight()
	scope := "Project · this workspace"
	if s.scope == 1 {
		scope = "User · all workspaces"
	}
	nameView := fitLine(s.name.View(), width)
	if s.focus == "name" {
		nameView = selectedStyle.Render(nameView)
	}
	scopeView := "Scope  " + scope + "  ←/→"
	if s.focus == "scope" {
		scopeView = selectedStyle.Render(scopeView)
	}
	title := "Content · $ARGUMENTS inserts your arguments"
	if s.readOnly {
		title = "Content · read-only (load failed)"
	}
	content := s.content
	content.SetSize(max(1, width-4), max(1, height-8))
	state := "All changes saved"
	if s.mode == "create" {
		state = "New template · Ctrl+S saves"
	}
	if s.dirty() {
		state = "● Unsaved changes · Ctrl+S saves"
	}
	if s.status != "" {
		state = s.status
	}
	position := fmt.Sprintf("Ln %d, Col %d · %d characters", s.content.CaretLine+1, s.content.CaretCol+1, len([]rune(s.content.Text())))
	if height < 10 {
		content.SetSize(max(1, width-4), max(1, height-4))
		return nameView + "\n" + scopeView + "\n" + content.View() + "\n" + dimStyle.Render(fitLine(position, width)) + "\n" + fitLine(state, width)
	}
	return nameView + "\n" + scopeView + "\n" + pane(title, content.View(), width, max(4, height-5), s.focus == "content") + "\n" + dimStyle.Render(fitLine(position, width)) + "\n" + statusStyle.Render(fitLine(state, width))
}
func (s *TemplateScreen) Hints() []Hint {
	if s.discardPending {
		return []Hint{{"esc", "discard changes"}, {"ctrl+s", "save instead"}, {"type", "keep editing"}}
	}
	if s.quitPending {
		return []Hint{{"ctrl+q", "discard & quit"}, {"ctrl+s", "save instead"}, {"esc", "cancel"}}
	}
	if s.confirmedDelete != "" {
		return []Hint{{"ctrl+d", "confirm delete"}, {"esc", "cancel"}}
	}
	if s.confirmedTarget != "" {
		return []Hint{{"ctrl+s", "confirm overwrite"}, {"esc", "cancel"}}
	}
	hints := []Hint{{"tab/shift+tab", "field"}, {"ctrl+s", "save"}, {"ctrl+z/y", "undo/redo"}}
	if s.mode == "edit" {
		hints = append(hints, Hint{"ctrl+d", "delete"})
	}
	return append(hints, Hint{"esc", "back"})
}
