// Package tui implements PromptCraft's keyboard-first terminal workspace.
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

type Hint struct{ Key, Label string }
type Toast struct {
	Message, Severity string
	ExpiresAt         time.Time
}

type Screen interface {
	Init() tea.Cmd
	Update(tea.Msg) (Screen, tea.Cmd)
	View() string
	Hints() []Hint
}

// App shares dependencies and owns navigation. All mutations happen in Update.
type App struct {
	core          *core.Processor
	deps          clipboard.Deps
	out           io.Writer
	width, height int
	stack         []Screen
	toast         *Toast
	quitting      bool
	Now           func() time.Time
	pendingPush   Screen
	pendingPop    bool
}

func NewApp(processor *core.Processor, deps clipboard.Deps, out io.Writer) *App {
	deps.OSC52Writer = func(text string) error {
		_, err := fmt.Fprint(out, clipboard.Sequence(text))
		return err
	}
	app := &App{core: processor, deps: deps, out: out, Now: time.Now, width: 80, height: 24}
	app.stack = []Screen{NewHomeScreen(app)}
	return app
}

func (a *App) Current() Screen    { return a.stack[len(a.stack)-1] }
func (a *App) Push(screen Screen) { a.pendingPush = screen }
func (a *App) Pop()               { a.pendingPop = true }
func (a *App) Quit()              { a.quitting = true }
func (a *App) bodyWidth() int     { return max(1, a.width-2) }
func (a *App) bodyHeight() int    { return max(1, a.height-7) }

func (a *App) Notify(message, severity string) {
	ttl := 4 * time.Second
	if severity == "warning" || severity == "error" {
		ttl = 8 * time.Second
	}
	a.toast = &Toast{Message: message, Severity: severity, ExpiresAt: a.Now().Add(ttl)}
}

func (a *App) expireToast() {
	if a.toast != nil && !a.Now().Before(a.toast.ExpiresAt) {
		a.toast = nil
	}
}

func (a *App) toastExpiry() time.Time {
	if a.toast == nil {
		return time.Time{}
	}
	return a.toast.ExpiresAt
}

type Model struct{ app *App }

func NewModel(app *App) *Model { return &Model{app: app} }
func (m *Model) Init() tea.Cmd { return m.app.Current().Init() }

type resumer interface{ Resume() }
type toastExpiredMsg struct{ deadline time.Time }

func toastTickCmd(delay time.Duration, expiry time.Time) tea.Cmd {
	return tea.Tick(max(0, delay), func(time.Time) tea.Msg { return toastExpiredMsg{deadline: expiry} })
}

func (m *Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	if key, ok := msg.(tea.KeyMsg); ok && (key.String() == "ctrl+q" || key.String() == "ctrl+c") {
		if editor, ok := m.app.Current().(*TemplateScreen); ok && editor.dirty() {
			cmd := editor.requestQuit()
			if m.app.quitting {
				return m, cmd
			}
			deadline := m.app.toastExpiry()
			return m, tea.Batch(cmd, toastTickCmd(deadline.Sub(m.app.Now()), deadline))
		}
		m.app.Quit()
		return m, tea.Quit
	}
	if size, ok := msg.(tea.WindowSizeMsg); ok {
		m.app.width, m.app.height = max(1, size.Width), max(1, size.Height)
		// Inactive screens must also resize before they are resumed.
		for i, screen := range m.app.stack {
			updated, _ := screen.Update(size)
			m.app.stack[i] = updated
		}
		return m, nil
	}
	expiry := m.app.toastExpiry()
	m.app.expireToast()
	if tick, ok := msg.(toastExpiredMsg); ok {
		if m.app.toast != nil && tick.deadline.Equal(m.app.toast.ExpiresAt) {
			m.app.toast = nil
		}
		return m, nil
	}
	updated, cmd := m.app.Current().Update(msg)
	m.app.stack[len(m.app.stack)-1] = updated
	if m.app.pendingPush != nil {
		pushed := m.app.pendingPush
		m.app.pendingPush = nil
		m.app.stack = append(m.app.stack, pushed)
		_, sizeCmd := pushed.Update(tea.WindowSizeMsg{Width: m.app.width, Height: m.app.height})
		cmd = tea.Batch(cmd, sizeCmd, pushed.Init())
	}
	if m.app.pendingPop {
		if len(m.app.stack) > 1 {
			m.app.stack = m.app.stack[:len(m.app.stack)-1]
			if screen, ok := m.app.Current().(resumer); ok {
				screen.Resume()
			}
		}
		m.app.pendingPop = false
	}
	// Schedule only new notifications; stale timers cannot erase newer ones.
	deadline := m.app.toastExpiry()
	if !deadline.IsZero() && !deadline.Equal(expiry) {
		cmd = tea.Batch(cmd, toastTickCmd(deadline.Sub(m.app.Now()), deadline))
	}
	return m, cmd
}

func screenTitle(screen Screen) string {
	switch s := screen.(type) {
	case *HomeScreen:
		return "Template library"
	case *RunScreen:
		return "Run /" + s.template.Name
	case *ResultScreen:
		return "Generated prompt"
	case *TemplateScreen:
		if s.mode == "edit" {
			return "Edit /" + s.template.Name
		}
		return "New template"
	case *HelpScreen:
		return "Keyboard guide"
	case *VersionScreen:
		return "About"
	case *InitResultScreen:
		return "Project setup"
	default:
		return "PromptCraft"
	}
}

func (m *Model) View() string {
	if m.app.quitting {
		return ""
	}
	w, h := m.app.width, m.app.height
	if w < 40 || h < 12 {
		return fitBlock("PromptCraft\nResize the terminal to at least 40 × 12.\nCtrl+Q to quit", w, h)
	}
	screen := m.app.Current()
	width := m.app.bodyWidth()
	brand := headerStyle.Render("◆ PromptCraft")
	title := dimStyle.Render(" / " + screenTitle(screen))
	versionText := dimStyle.Render("v" + version.Version)
	left := fitLine(brand+title, max(1, width-lipgloss.Width(versionText)-1))
	header := left + strings.Repeat(" ", max(1, width-lipgloss.Width(left)-lipgloss.Width(versionText))) + versionText
	notification := dimStyle.Render("Ready · ? opens the keyboard guide")
	if m.app.toast != nil {
		notification = toastStyle(m.app.toast.Severity).Render(m.app.toast.Message)
	}
	body := fitBlock(screen.View(), width, m.app.bodyHeight())
	return fitBlock(strings.Join([]string{header, dimStyle.Render(strings.Repeat("─", width)), body, "", fitLine(notification, width), hintRows(screen.Hints(), width)}, "\n"), w, h)
}

func Run(processor *core.Processor, deps clipboard.Deps, out io.Writer) error {
	program := tea.NewProgram(NewModel(NewApp(processor, deps, out)), tea.WithOutput(out), tea.WithAltScreen())
	_, err := program.Run()
	return err
}
