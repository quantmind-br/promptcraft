// Package tui implements the interactive terminal interface with Bubble Tea.
//
// The screens mirror the legacy Textual interface: a template list, a run form,
// a result view, a template editor, and feedback panels for initialization,
// version, and help.
package tui

import (
	"fmt"
	"io"
	"strings"
	"time"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/quantmind-br/promptcraft/internal/clipboard"
	"github.com/quantmind-br/promptcraft/internal/core"
	"github.com/quantmind-br/promptcraft/internal/version"
)

// Hint is one entry of the keymap footer.
type Hint struct {
	Key   string
	Label string
}

// Toast is a transient notification shown under the status line.
type Toast struct {
	Message   string
	Severity  string
	ExpiresAt time.Time
}

// Screen is one layer of the interface stack.
type Screen interface {
	Init() tea.Cmd
	Update(tea.Msg) (Screen, tea.Cmd)
	View() string
	Hints() []Hint
}

// App holds the state shared by all screens.
type App struct {
	core *core.Processor
	deps clipboard.Deps
	out  io.Writer

	width    int
	height   int
	stack    []Screen
	toast    *Toast
	quitting bool

	Now         func() time.Time
	pendingPush Screen
	pendingPop  bool
}

// NewApp returns an app whose OSC 52 writes go through the program output, so
// they do not interleave with rendering.
func NewApp(processor *core.Processor, deps clipboard.Deps, out io.Writer) *App {
	deps.OSC52Writer = func(text string) error {
		_, err := fmt.Fprint(out, clipboard.Sequence(text))
		return err
	}
	app := &App{core: processor, deps: deps, out: out, Now: time.Now}
	app.stack = []Screen{NewHomeScreen(app)}
	return app
}

// Current returns the active screen.
func (a *App) Current() Screen { return a.stack[len(a.stack)-1] }

// Push puts a screen on top of the stack.
func (a *App) Push(screen Screen) { a.pendingPush = screen }

// Pop returns to the previous screen.
func (a *App) Pop() { a.pendingPop = true }

// Quit ends the program.
func (a *App) Quit() { a.quitting = true }

// Notify records a toast with the given severity and TTL, mirroring the legacy
// notification semantics.
func (a *App) Notify(message, severity string) {
	ttl := time.Duration(0)
	switch severity {
	case "warning", "error":
		ttl = 8 * time.Second
	}
	expiry := a.Now()
	if ttl > 0 {
		expiry = expiry.Add(ttl)
	}
	a.toast = &Toast{Message: message, Severity: severity, ExpiresAt: expiry}
}

func (a *App) expireToast() {
	if a.toast == nil {
		return
	}
	if a.Now().After(a.toast.ExpiresAt) {
		a.toast = nil
	}
}

// Model is the Bubble Tea model wrapping the screen stack.
type Model struct {
	app *App
}

// NewModel returns the root model for an app.
func NewModel(app *App) *Model { return &Model{app: app} }

// Init starts on the home screen.
func (m *Model) Init() tea.Cmd { return m.app.Current().Init() }

// Update dispatches messages to the active screen and applies navigation.
func (m *Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	if key, ok := msg.(tea.KeyMsg); ok && key.String() == "ctrl+q" {
		m.app.Quit()
		return m, tea.Quit
	}
	if size, ok := msg.(tea.WindowSizeMsg); ok {
		m.app.width, m.app.height = size.Width, size.Height
	}
	m.app.expireToast()

	screen := m.app.Current()
	updated, cmd := screen.Update(msg)
	m.app.stack[len(m.app.stack)-1] = updated

	if m.app.pendingPush != nil {
		m.app.stack = append(m.app.stack, m.app.pendingPush)
		m.app.pendingPush = nil
	}
	if m.app.pendingPop && len(m.app.stack) > 1 {
		m.app.stack = m.app.stack[:len(m.app.stack)-1]
		m.app.pendingPop = false
	}

	return m, cmd
}

// View renders the header, the active screen, the toast, and the keymap footer.
func (m *Model) View() string {
	if m.app.quitting {
		return ""
	}
	screen := m.app.Current()
	lines := []string{headerStyle.Render("PromptCraft v" + version.Version), screen.View()}
	if m.app.toast != nil {
		lines = append(lines, toastStyle(m.app.toast.Severity).Render(m.app.toast.Message))
	}
	lines = append(lines, renderHints(screen.Hints()))
	return strings.Join(lines, "\n")
}

// Run starts the interactive interface.
func Run(processor *core.Processor, deps clipboard.Deps, out io.Writer) error {
	app := NewApp(processor, deps, out)
	program := tea.NewProgram(NewModel(app), tea.WithOutput(out))
	_, err := program.Run()
	return err
}

var (
	headerStyle = lipgloss.NewStyle().Bold(true)
	statusStyle = lipgloss.NewStyle()
	dimStyle    = lipgloss.NewStyle().Faint(true)
	errorStyle  = lipgloss.NewStyle().Foreground(lipgloss.Color("1"))
	warnStyle   = lipgloss.NewStyle().Foreground(lipgloss.Color("3"))
	infoStyle   = lipgloss.NewStyle().Foreground(lipgloss.Color("2"))
	panelStyle  = lipgloss.NewStyle().Border(lipgloss.RoundedBorder()).Padding(0, 1)
	footerStyle = lipgloss.NewStyle()
	keyStyle    = lipgloss.NewStyle().Bold(true)
)

func toastStyle(severity string) lipgloss.Style {
	switch severity {
	case "error":
		return errorStyle
	case "warning":
		return warnStyle
	default:
		return infoStyle
	}
}

func renderHints(hints []Hint) string {
	parts := make([]string, 0, len(hints))
	for _, hint := range hints {
		parts = append(parts, keyStyle.Render(hint.Key)+" "+dimStyle.Render(hint.Label))
	}
	return footerStyle.Render(strings.Join(parts, " · "))
}
