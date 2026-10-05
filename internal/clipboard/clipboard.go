// Package clipboard copies generated prompts through the host clipboard tools
// or through the terminal with an OSC 52 write.
package clipboard

import (
	"context"
	"encoding/base64"
	"fmt"
	"os"
	"runtime"
	"strings"
	"time"

	atotto "github.com/atotto/clipboard"
)

// Routes reported by Copy.
const (
	RouteNative = "native" // host clipboard tools
	RouteOSC52  = "osc52"  // terminal escape sequence, forwarded by herdr / SSH terminals
)

// herdr discards OSC 52 writes whose decoded text exceeds 192 KiB.
const MaxOSC52Bytes = 192 * 1024

// Budget for a host clipboard copy.
const NativeTimeout = 150 * time.Millisecond

// Controlling terminal used for OSC 52 writes outside the TUI.
var TTYPath = "/dev/tty"

// Deps holds the environment snapshot and the injectable backends, so tests can
// run without touching a real clipboard or terminal.
type Deps struct {
	Env        map[string]string
	FileExists func(string) bool
	TTYPath    string
	NativeCopy func(text string) error
	// NativeCopyWithContext is preferred when the backend can be cancelled, so a
	// timed-out copy does not leave an orphan goroutine behind.
	NativeCopyWithContext func(ctx context.Context, text string) error
	OSC52Writer           func(text string) error
}

// Default returns deps wired to the process environment and the real backends.
func Default() Deps {
	env := map[string]string{}
	for _, entry := range os.Environ() {
		key, value, ok := strings.Cut(entry, "=")
		if !ok {
			continue
		}
		env[key] = value
	}
	return Deps{
		Env:         env,
		FileExists:  func(path string) bool { _, err := os.Stat(path); return err == nil },
		TTYPath:     TTYPath,
		NativeCopy:  atotto.WriteAll,
		OSC52Writer: func(text string) error { return WriteToTTY(Deps{Env: env, TTYPath: TTYPath}, text) },
	}
}

// Sequence builds an OSC 52 clipboard write for the given text.
func Sequence(text string) string {
	encoded := base64.StdEncoding.EncodeToString([]byte(text))
	return fmt.Sprintf("\x1b]52;c;%s\x07", encoded)
}

// WriteToTTY emits the OSC 52 sequence on the controlling terminal.
func WriteToTTY(d Deps, text string) error {
	path := d.TTYPath
	if path == "" {
		path = TTYPath
	}
	file, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE, 0o644)
	if err != nil {
		return err
	}
	defer func() { _ = file.Close() }()
	_, err = fmt.Fprint(file, Sequence(text))
	return err
}

// Copy sends text to the clipboard and reports the route that carried it.
//
// Inside herdr or over SSH the native clipboard belongs to the host running the
// process, so the copy goes through the terminal. A failing native copy also
// falls back to OSC 52. Returns an empty string when nothing was copied.
func Copy(text string, d Deps) string {
	mode := strings.ToLower(strings.TrimSpace(d.Env["PROMPTCRAFT_CLIPBOARD"]))
	// An explicit mode is authoritative; otherwise the environment decides.
	terminalOnly := mode == RouteOSC52 || (mode != RouteNative && (PreferOSC52(d) || Headless(d)))
	if terminalOnly && ClipboardDisabled(d) {
		return ""
	}
	if !terminalOnly && copyNative(d, text) {
		return RouteNative
	}
	if copyOSC52(d, text) {
		return RouteOSC52
	}
	return ""
}

func copyNative(d Deps, text string) bool {
	if d.NativeCopyWithContext != nil {
		ctx, cancel := context.WithTimeout(context.Background(), NativeTimeout)
		defer cancel()
		return d.NativeCopyWithContext(ctx, text) == nil
	}
	if d.NativeCopy == nil {
		return false
	}
	done := make(chan error, 1)
	go func() { done <- d.NativeCopy(text) }()
	select {
	case err := <-done:
		return err == nil
	case <-time.After(NativeTimeout):
		return false
	}
}

// copyOSC52 reports whether the sequence was emitted. The terminal never
// acknowledges an OSC 52 write, so success only means it was sent.
func copyOSC52(d Deps, text string) bool {
	size := len([]byte(text))
	if size == 0 || size > MaxOSC52Bytes {
		return false
	}
	writer := d.OSC52Writer
	if writer == nil {
		writer = func(value string) error { return WriteToTTY(d, value) }
	}
	if err := writer(text); err != nil {
		return false
	}
	return true
}

// PreferOSC52 reports whether the clipboard must be reached through the terminal.
//
// A herdr pane cannot tell whether the attached client is local, over SSH, or
// `herdr --remote`, and inherits the server's DISPLAY/WAYLAND_DISPLAY, so a
// native copy may land on the wrong machine. PROMPTCRAFT_CLIPBOARD=osc52|native
// overrides the detection.
func PreferOSC52(d Deps) bool {
	mode := strings.ToLower(strings.TrimSpace(d.Env["PROMPTCRAFT_CLIPBOARD"]))
	if mode == RouteOSC52 || mode == RouteNative {
		return mode == RouteOSC52
	}
	if d.Env["HERDR_ENV"] == "1" {
		return true
	}
	for _, name := range []string{"SSH_CONNECTION", "SSH_TTY", "SSH_CLIENT"} {
		if d.Env[name] != "" {
			return true
		}
	}
	return false
}

// ClipboardDisabled reports whether every clipboard route is turned off (CI or
// manual override).
func ClipboardDisabled(d Deps) bool {
	return d.Env["CI"] == "true" || d.Env["PROMPTCRAFT_NO_CLIPBOARD"] == "true"
}

// Headless reports an environment where the native clipboard may be unavailable
// while the terminal may still accept OSC 52.
func Headless(d Deps) bool {
	if ClipboardDisabled(d) {
		return true
	}
	// A Wayland session has a working native clipboard even without X11.
	if d.Env["WAYLAND_DISPLAY"] != "" {
		return false
	}
	if value, ok := d.Env["DISPLAY"]; ok && value == "" {
		return true
	}
	if d.Env["SSH_CLIENT"] != "" && d.Env["DISPLAY"] == "" {
		return true
	}
	if strings.HasPrefix(runtime.GOOS, "linux") {
		if d.Env["DISPLAY"] == "" && d.FileExists != nil && !d.FileExists("/tmp/.X11-unix") {
			return true
		}
	}
	return false
}
