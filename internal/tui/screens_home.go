package tui

import (
	"errors"
	"fmt"
	"io/fs"
	"strings"

	"github.com/charmbracelet/bubbles/key"
	"github.com/charmbracelet/bubbles/list"
	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/quantmind-br/promptcraft/internal/core"
)

// HomeScreen is a searchable library with a preview of the selected template.
type HomeScreen struct {
	app                                               *App
	list                                              list.Model
	search                                            textinput.Model
	status, details, confirmedDelete, highlightedName string
	templates, allTemplates                           []core.CommandInfo
	preview                                           string
}

func NewHomeScreen(app *App) *HomeScreen {
	input := textinput.New()
	input.Prompt = "Search  / "
	input.Placeholder = "name, description or source"
	input.TextStyle = headerStyle
	screen := &HomeScreen{app: app, list: list.New(nil, templateDelegate{}, 60, 10), search: input}
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

func listCursorKeyMap() list.KeyMap {
	empty := key.NewBinding()
	return list.KeyMap{
		CursorUp:   key.NewBinding(key.WithKeys("up", "k")),
		CursorDown: key.NewBinding(key.WithKeys("down", "j")),
		NextPage:   key.NewBinding(key.WithKeys("pgdown")), PrevPage: key.NewBinding(key.WithKeys("pgup")),
		GoToStart: key.NewBinding(key.WithKeys("home")), GoToEnd: key.NewBinding(key.WithKeys("end")),
		Filter: empty, ClearFilter: empty, CancelWhileFiltering: empty, AcceptWhileFiltering: empty,
		ShowFullHelp: empty, CloseFullHelp: empty, Quit: empty, ForceQuit: empty,
	}
}

func (s *HomeScreen) Init() tea.Cmd { return nil }
func (s *HomeScreen) populateList(keepHighlight string) {
	s.allTemplates = s.app.core.ListTemplates()
	s.applyFilter(keepHighlight)
}

func (s *HomeScreen) applyFilter(keepHighlight string) {
	query := strings.ToLower(strings.TrimSpace(s.search.Value()))
	s.templates = nil
	items := []list.Item{}
	for _, template := range s.allTemplates {
		if query != "" && !strings.Contains(strings.ToLower(template.Name+" "+template.Description+" "+template.Source), query) {
			continue
		}
		s.templates = append(s.templates, template)
		items = append(items, templateItem{info: template})
	}
	s.list.SetItems(items)
	s.list.Select(0)
	for i, template := range s.templates {
		if template.Name == keepHighlight {
			s.list.Select(i)
			break
		}
	}
	s.confirmedDelete = ""
	s.highlightedName, s.details, s.preview = "", "", ""
	if template := s.selected(); template != nil {
		s.highlight(*template)
	}
}

func (s *HomeScreen) highlight(template core.CommandInfo) {
	if s.confirmedDelete != "" && s.confirmedDelete != template.Path {
		s.confirmedDelete, s.status = "", ""
		s.app.toast = nil
	}
	s.highlightedName = template.Name
	s.details = fmt.Sprintf("/%s  ·  [%s]  ·  %s", template.Name, template.Source, template.Path)
	content, err := s.app.core.LoadTemplateContent(template.Path)
	if err != nil {
		s.preview = "Could not read the preview: " + err.Error()
		return
	}
	s.preview = content
}

func (s *HomeScreen) Resume() { s.populateList(s.highlightedName) }
func (s *HomeScreen) selected() *core.CommandInfo {
	index := s.list.Index()
	if index < 0 || index >= len(s.templates) {
		return nil
	}
	return &s.templates[index]
}

func (s *HomeScreen) Update(msg tea.Msg) (Screen, tea.Cmd) {
	switch message := msg.(type) {
	case tea.WindowSizeMsg:
		width, _, _ := s.libraryGeometry()
		s.search.Width = max(1, width-14)
		return s, nil
	case tea.KeyMsg:
		name := keyName(message)
		if s.search.Focused() {
			switch name {
			case "esc":
				s.search.SetValue("")
				s.search.Blur()
				s.applyFilter(s.highlightedName)
				return s, nil
			case "enter", "tab":
				s.search.Blur()
				return s, nil
			case "up", "down", "pgup", "pgdown":
				return s, s.move(message)
			}
			var cmd tea.Cmd
			s.search, cmd = s.search.Update(message)
			s.applyFilter(s.highlightedName)
			return s, cmd
		}
		switch name {
		case "up", "down", "j", "k", "home", "end", "pgup", "pgdown":
			return s, s.move(message)
		case "/", "ctrl+f":
			s.confirmedDelete, s.status = "", ""
			return s, s.search.Focus()
		case "enter", "r":
			if template := s.selected(); template != nil {
				s.app.Push(NewRunScreen(s.app, *template))
			} else {
				s.app.Notify("Select a template first (Up/Down, then Enter).", "warning")
			}
		case "n":
			s.app.Push(NewTemplateScreen(s.app, "create", core.CommandInfo{}))
		case "e":
			if template := s.selected(); template != nil {
				s.app.Push(NewTemplateScreen(s.app, "edit", *template))
			} else {
				s.app.Notify("Select the template to edit first (Up/Down, then e).", "warning")
			}
		case "d":
			return s, s.deleteSelected()
		case "i":
			return s, s.initialize()
		case "v":
			s.app.Push(NewVersionScreen(s.app))
		case "f":
			s.app.core.InvalidateCaches()
			s.populateList(s.highlightedName)
			s.app.Notify("Template list refreshed.", "information")
		case "?":
			s.app.Push(NewHelpScreen(s.app))
		case "q", "esc":
			if s.confirmedDelete != "" {
				s.confirmedDelete, s.status, s.app.toast = "", "Delete cancelled.", nil
			} else if s.search.Value() != "" {
				s.search.SetValue("")
				s.applyFilter(s.highlightedName)
			} else {
				s.app.Quit()
				return s, tea.Quit
			}
		}
	}
	return s, nil
}

func (s *HomeScreen) move(message tea.KeyMsg) tea.Cmd {
	// Pagination uses the same geometry as the rendered library pane.
	w, h, _ := s.libraryGeometry()
	s.list.SetDelegate(templateDelegate{compact: h < 10})
	s.list.SetSize(max(1, w-4), max(1, h-4))
	var cmd tea.Cmd
	s.list, cmd = s.list.Update(message)
	if template := s.selected(); template != nil {
		s.highlight(*template)
	}
	return cmd
}

func (s *HomeScreen) deleteSelected() tea.Cmd {
	template := s.selected()
	if template == nil {
		s.app.Notify("Select the template to delete first (Up/Down, then d).", "warning")
		return nil
	}
	if template.Path != s.confirmedDelete {
		s.confirmedDelete = template.Path
		s.status = fmt.Sprintf("⚠ Delete '/%s' [%s]? Press d again to confirm. Esc cancels.", template.Name, template.Source)
		return nil
	}
	s.confirmedDelete = ""
	if err := s.app.core.DeleteTemplate(template.Path); err != nil {
		if errors.Is(err, fs.ErrNotExist) {
			s.status = fmt.Sprintf("⚠ /%s was already deleted. List refreshed.", template.Name)
			s.populateList("")
		} else {
			s.status = "✗ Delete failed: " + err.Error()
			s.app.Notify(s.status, "error")
		}
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
		s.status = "✗ " + result.Error
		s.app.Notify(result.Error, "error")
		return nil
	}
	s.status = "✓ Project structure ready (see details)."
	s.app.Push(NewInitResultScreen(s.app, result))
	return nil
}

func (s *HomeScreen) libraryGeometry() (int, int, bool) {
	width, height := s.app.bodyWidth(), max(3, s.app.bodyHeight()-2)
	if width >= 94 {
		return width * 2 / 5, height, true
	}
	if height >= 15 {
		return width, height - 7, false
	}
	return width, height, false
}

func (s *HomeScreen) previewView(width, height int) string {
	template := s.selected()
	if template == nil {
		return pane("Preview", dimStyle.Render("Select a template to explore its content."), width, height, false)
	}
	inner := max(1, width-4)
	metadata := headerStyle.Render("/"+template.Name) + "  " + dimStyle.Render("["+template.Source+"]")
	path := dimStyle.Render(fitLine(template.Path, inner))
	content := metadata + "\n" + path + "\n\n" + wrapText(s.preview, inner)
	if height < 8 {
		content = metadata + "\n" + wrapText(s.preview, inner)
	}
	return pane("Preview · Enter to run", content, width, height, false)
}

func (s *HomeScreen) View() string {
	width, height, split := s.libraryGeometry()
	if s.app.bodyHeight() < 8 {
		rows := []string{headerStyle.Render(fmt.Sprintf("Templates · %d", len(s.templates)))}
		if s.search.Focused() || s.search.Value() != "" {
			rows = append(rows, fitLine(s.search.View(), s.app.bodyWidth()))
		}
		if len(s.templates) == 0 {
			rows = append(rows, "No templates found. Press n or i.")
		} else {
			available := max(1, s.app.bodyHeight()-len(rows)-1)
			start := max(0, s.list.Index()-available+1)
			for i := start; i < min(start+available, len(s.templates)); i++ {
				label := "  /" + s.templates[i].Name + " [" + s.templates[i].Source + "]"
				if i == s.list.Index() {
					label = selectedStyle.Render("› /" + s.templates[i].Name + " [" + s.templates[i].Source + "]")
				}
				rows = append(rows, fitLine(label, s.app.bodyWidth()))
			}
		}
		rows = append(rows, fitLine(s.status, s.app.bodyWidth()))
		return strings.Join(rows, "\n")
	}
	listView := s.list
	listView.SetDelegate(templateDelegate{compact: height < 10})
	listView.SetSize(max(1, width-4), max(1, height-4))
	content := s.search.View() + "\n" + listView.View()
	if len(s.allTemplates) == 0 {
		content = "No templates found.\n\n" + headerStyle.Render("Your prompt workspace starts here.") + "\n" + wrapText("Press n to create your first template, or i to set up this project with an example.", max(1, width-4))
	} else if len(s.templates) == 0 {
		content = s.search.View() + "\n\nNo matches. Try another search or Esc to reset."
	}
	title := fmt.Sprintf("Templates · %d", len(s.allTemplates))
	if s.search.Value() != "" {
		title = fmt.Sprintf("Templates · %d/%d matches", len(s.templates), len(s.allTemplates))
	}
	library := pane(title, content, width, height, !s.search.Focused())
	if split {
		library = lipgloss.JoinHorizontal(lipgloss.Top, library, " ", s.previewView(s.app.bodyWidth()-width-1, height))
	} else if s.app.bodyHeight()-2 >= 15 {
		library += "\n" + s.previewView(width, 6)
	}
	details := s.status
	if details == "" {
		details = s.details
	}
	return library + "\n" + fitLine(statusStyle.Render(details), s.app.bodyWidth())
}

func (s *HomeScreen) Hints() []Hint {
	if s.search.Focused() {
		return []Hint{{"type", "search"}, {"↑/↓", "select"}, {"enter", "apply"}, {"esc", "clear"}}
	}
	if s.confirmedDelete != "" {
		return []Hint{{"d", "confirm delete"}, {"esc", "cancel"}}
	}
	return []Hint{{"↑/↓", "move"}, {"enter", "run"}, {"/", "search"}, {"n", "new"}, {"e", "edit"}, {"d", "delete"}, {"i", "setup"}, {"f", "refresh"}, {"?", "help"}, {"q", "quit"}}
}
