package tui

import (
	"errors"
	"fmt"
	"io/fs"

	"github.com/charmbracelet/bubbles/key"
	"github.com/charmbracelet/bubbles/list"
	tea "github.com/charmbracelet/bubbletea"

	"github.com/quantmind-br/promptcraft/internal/core"
)

// HomeScreen is the template list with the main actions.
type HomeScreen struct {
	app             *App
	list            list.Model
	status          string
	details         string
	confirmedDelete string
	templates       []core.CommandInfo
	highlightedName string
}

// NewHomeScreen builds the home screen and loads the template list.
func NewHomeScreen(app *App) *HomeScreen {
	screen := &HomeScreen{app: app, list: list.New(nil, templateDelegate{}, 60, 10)}
	screen.list.SetFilteringEnabled(false)
	screen.list.SetShowTitle(false)
	screen.list.SetShowFilter(false)
	screen.list.SetShowStatusBar(false)
	screen.list.SetShowPagination(false)
	screen.list.SetShowHelp(false)
	screen.list.KeyMap = listCursorKeyMap()
	screen.populateList("")
	return screen
}

// listCursorKeyMap keeps only Up/Down on the list so every other shortcut stays
// with the screen.
func listCursorKeyMap() list.KeyMap {
	empty := key.NewBinding()
	return list.KeyMap{
		CursorUp:             key.NewBinding(key.WithKeys("up")),
		CursorDown:           key.NewBinding(key.WithKeys("down")),
		NextPage:             empty,
		PrevPage:             empty,
		GoToStart:            empty,
		GoToEnd:              empty,
		Filter:               empty,
		ClearFilter:          empty,
		CancelWhileFiltering: empty,
		AcceptWhileFiltering: empty,
		ShowFullHelp:         empty,
		CloseFullHelp:        empty,
		Quit:                 empty,
		ForceQuit:            empty,
	}
}

// Init starts with the first template highlighted.
func (s *HomeScreen) Init() tea.Cmd { return nil }

func (s *HomeScreen) populateList(keepHighlight string) {
	s.templates = s.app.core.ListTemplates()

	items := make([]list.Item, 0, len(s.templates))
	for _, template := range s.templates {
		items = append(items, templateItem{info: template})
	}
	s.list.SetItems(items)

	if keepHighlight != "" {
		for index, template := range s.templates {
			if template.Name == keepHighlight {
				s.list.Select(index)
				s.highlight(template)
				break
			}
		}
	} else {
		s.highlightedName = ""
		s.details = ""
	}

	s.confirmedDelete = ""
}

func (s *HomeScreen) highlight(template core.CommandInfo) {
	if template.Name == "" {
		s.highlightedName = ""
		return
	}
	s.highlightedName = template.Name
	s.details = fmt.Sprintf("/%s  ·  [%s]  ·  %s", template.Name, template.Source, template.Path)
}

func (s *HomeScreen) selected() *core.CommandInfo {
	if len(s.templates) == 0 {
		return nil
	}
	template := s.templates[s.list.Index()]
	return &template
}

// Update dispatches keys: arrows move the cursor, letters run actions.
func (s *HomeScreen) Update(msg tea.Msg) (Screen, tea.Cmd) {
	switch message := msg.(type) {
	case tea.WindowSizeMsg:
		s.list.SetWidth(message.Width)
		s.list.SetHeight(max(1, message.Height-5))
		return s, nil
	case tea.KeyMsg:
		name := keyName(message)
		if name == "up" || name == "down" {
			var cmd tea.Cmd
			s.list, cmd = s.list.Update(message)
			if len(s.templates) > 0 {
				s.highlight(s.templates[s.list.Index()])
			}
			return s, cmd
		}

		switch name {
		case "enter", "r":
			if template := s.selected(); template != nil {
				s.app.Push(NewRunScreen(s.app, *template))
			} else {
				s.app.Notify("Select a template first (Up/Down, then Enter).", "warning")
			}
			return s, nil
		case "n":
			s.app.Push(NewTemplateScreen(s.app, "create", core.CommandInfo{}))
			return s, nil
		case "e":
			template := s.selected()
			if template == nil {
				s.app.Notify("Select the template to edit first (Up/Down, then e).", "warning")
				return s, nil
			}
			s.app.Push(NewTemplateScreen(s.app, "edit", *template))
			return s, nil
		case "d":
			return s, s.deleteSelected()
		case "i":
			return s, s.initialize()
		case "v":
			s.app.Push(NewVersionScreen(s.app))
			return s, nil
		case "f":
			s.populateList("")
			s.app.Notify("Template list refreshed.", "information")
			return s, nil
		case "?":
			s.app.Push(NewHelpScreen(s.app))
			return s, nil
		case "q", "esc":
			if s.confirmedDelete != "" {
				s.confirmedDelete = ""
				s.status = "Delete cancelled."
				return s, nil
			}
			s.app.Quit()
			return s, tea.Quit
		}
	}
	return s, nil
}

func (s *HomeScreen) deleteSelected() tea.Cmd {
	template := s.selected()
	if template == nil {
		s.app.Notify("Select the template to delete first (Up/Down, then d).", "warning")
		return nil
	}

	pathKey := template.Path
	if pathKey != s.confirmedDelete {
		s.confirmedDelete = pathKey
		message := fmt.Sprintf("⚠ Delete '/%s' [%s] (%s)? Press d again to confirm.", template.Name, template.Source, template.Path)
		s.status = message
		s.app.Notify(message, "warning")
		return nil
	}

	s.confirmedDelete = ""
	if err := s.app.core.DeleteTemplate(template.Path); err != nil {
		if errors.Is(err, fs.ErrNotExist) {
			s.status = fmt.Sprintf("⚠ /%s was already deleted. List refreshed.", template.Name)
			s.app.Notify(fmt.Sprintf("/%s was already deleted.", template.Name), "warning")
			s.populateList("")
			return nil
		}
		s.status = "✗ Delete failed: " + err.Error()
		s.app.Notify("Delete failed: "+err.Error(), "error")
		return nil
	}

	s.status = fmt.Sprintf("✓ Deleted /%s [%s].", template.Name, template.Source)
	s.app.Notify(fmt.Sprintf("Deleted /%s", template.Name), "information")
	s.populateList("")
	return nil
}

func (s *HomeScreen) initialize() tea.Cmd {
	result := s.app.core.InitProject()
	if result.Error != "" {
		s.app.Notify(result.Error, "error")
		s.status = "✗ " + result.Error
		return nil
	}
	s.status = "✓ Project structure ready (see details)."
	s.app.Push(NewInitResultScreen(s.app, result))
	return nil
}

// View renders the hint, the list, the details and the status line.
func (s *HomeScreen) View() string {
	hint := "No templates found."
	if len(s.templates) > 0 {
		hint = fmt.Sprintf("%d template(s)  ·  sources: .promptcraft/commands (project) and ~/.promptcraft/commands (user)", len(s.templates))
	}

	details := s.details
	if len(s.templates) == 0 {
		details = "Press n to create a template, or i to initialize the project structure."
	} else if details == "" {
		details = "No template selected. Use Up/Down, then Enter to run."
	}

	return fmt.Sprintf("%s\n%s\n%s\n%s", dimStyle.Render(hint), s.list.View(), details, statusStyle.Render(s.status))
}

// Hints lists the home keymap.
func (s *HomeScreen) Hints() []Hint {
	return []Hint{
		{"↑/↓", "move"}, {"enter", "run"}, {"n", "new"}, {"e", "edit"}, {"d", "delete"},
		{"i", "init"}, {"v", "version"}, {"f", "refresh"}, {"?", "help"}, {"q", "quit"},
	}
}
