package clipboard

import (
	"encoding/base64"
	"errors"
	"strings"
	"testing"
	"time"
)

func testDeps(env map[string]string) Deps {
	return Deps{
		Env: env,
		// The X11 socket is treated as present when the environment marks it.
		FileExists: func(path string) bool { return path == "/tmp/.X11-unix" && env["X11_SOCKET"] == "yes" },
		// Never let a test write to the controlling terminal of the runner.
		TTYPath: "/nonexistent/promptcraft-test-tty",
	}
}

func TestPreferOSC52Detection(t *testing.T) {
	cases := []struct {
		name string
		env  map[string]string
		want bool
	}{
		{"plain desktop", map[string]string{"DISPLAY": ":0"}, false},
		{"herdr pane", map[string]string{"DISPLAY": ":0", "HERDR_ENV": "1"}, true},
		{"ssh session", map[string]string{"SSH_CONNECTION": "1.2.3.4"}, true},
		{"ssh tty", map[string]string{"SSH_TTY": "/dev/tty1"}, true},
		{"ssh client", map[string]string{"SSH_CLIENT": "1.2.3.4 5 6"}, true},
		{"explicit override osc52", map[string]string{"PROMPTCRAFT_CLIPBOARD": "osc52"}, true},
		{"explicit override native wins over herdr", map[string]string{"PROMPTCRAFT_CLIPBOARD": "native", "HERDR_ENV": "1"}, false},
		{"empty ssh value is not a signal", map[string]string{"SSH_CONNECTION": ""}, false},
	}

	for _, testCase := range cases {
		if got := PreferOSC52(testDeps(testCase.env)); got != testCase.want {
			t.Fatalf("%s: got %v want %v", testCase.name, got, testCase.want)
		}
	}
}

func TestClipboardDisabledAndHeadless(t *testing.T) {
	if !ClipboardDisabled(testDeps(map[string]string{"CI": "true"})) {
		t.Fatal("CI must disable every clipboard route")
	}
	if !ClipboardDisabled(testDeps(map[string]string{"PROMPTCRAFT_NO_CLIPBOARD": "true"})) {
		t.Fatal("the manual override must disable every clipboard route")
	}

	cases := []struct {
		name string
		env  map[string]string
		want bool
	}{
		{"disabled environment", map[string]string{"CI": "true"}, true},
		{"DISPLAY set to empty", map[string]string{"DISPLAY": ""}, true},
		{"ssh without display", map[string]string{"SSH_CLIENT": "1.2.3.4"}, true},
		{"linux container without X11 socket", map[string]string{}, true},
		{"linux with X11 socket", map[string]string{"DISPLAY": ":0", "X11_SOCKET": "yes"}, false},
	}

	for _, testCase := range cases {
		if got := Headless(testDeps(testCase.env)); got != testCase.want {
			t.Fatalf("%s: got %v want %v", testCase.name, got, testCase.want)
		}
	}
}

func TestCopyReportsTheRouteThatCarriedIt(t *testing.T) {
	native := testDeps(map[string]string{"DISPLAY": ":0"})
	native.NativeCopy = func(text string) error { return nil }
	native.OSC52Writer = func(text string) error { return nil }

	if route := Copy("prompt", native); route != RouteNative {
		t.Fatalf("expected the native route, got %q", route)
	}

	// A failing native copy falls back to the terminal.
	native.NativeCopy = func(text string) error { return errors.New("no backend") }
	if route := Copy("prompt", native); route != RouteOSC52 {
		t.Fatalf("expected the OSC 52 fallback, got %q", route)
	}

	// In a terminal-only environment the copy goes straight to the terminal.
	terminal := testDeps(map[string]string{"HERDR_ENV": "1"})
	terminal.NativeCopy = func(text string) error { return nil }
	terminal.OSC52Writer = func(text string) error { return nil }
	if route := Copy("prompt", terminal); route != RouteOSC52 {
		t.Fatalf("herdr sessions must use OSC 52, got %q", route)
	}

	// When everything fails, nothing is reported as copied.
	broken := testDeps(map[string]string{"DISPLAY": ":0"})
	broken.NativeCopy = func(text string) error { return errors.New("no backend") }
	broken.OSC52Writer = func(text string) error { return errors.New("not a terminal") }
	if route := Copy("prompt", broken); route != "" {
		t.Fatalf("failed routes must report nothing, got %q", route)
	}

	// A disabled clipboard reports nothing even when the writer works.
	disabled := testDeps(map[string]string{"CI": "true"})
	disabled.OSC52Writer = func(text string) error { return nil }
	if route := Copy("prompt", disabled); route != "" {
		t.Fatalf("disabled clipboard must not copy, got %q", route)
	}
}

func TestOSC52Limits(t *testing.T) {
	deps := testDeps(map[string]string{"HERDR_ENV": "1"})
	written := []string{}
	deps.OSC52Writer = func(text string) error {
		written = append(written, text)
		return nil
	}

	if route := Copy("", deps); route != "" {
		t.Fatalf("empty text must not be sent, got %q", route)
	}

	oversized := strings.Repeat("a", MaxOSC52Bytes+1)
	if route := Copy(oversized, deps); route != "" {
		t.Fatalf("payloads above the terminal limit must not be sent, got %q", route)
	}

	exact := strings.Repeat("a", MaxOSC52Bytes)
	if route := Copy(exact, deps); route != RouteOSC52 {
		t.Fatalf("a payload at the limit must be sent, got %q", route)
	}
	if len(written) != 1 || written[0] != exact {
		t.Fatalf("unexpected writes: %d", len(written))
	}
}

func TestNativeCopyRespectsTheTimeoutBudget(t *testing.T) {
	deps := testDeps(map[string]string{"DISPLAY": ":0"})
	deps.OSC52Writer = func(text string) error { return errors.New("writer unavailable") }

	slow := make(chan struct{})
	deps.NativeCopy = func(text string) error {
		<-slow
		return nil
	}

	start := time.Now()
	route := Copy("prompt", deps)
	elapsed := time.Since(start)
	if route != "" {
		t.Fatalf("a copy beyond the budget must not be reported, got %q", route)
	}
	if elapsed < NativeTimeout {
		t.Fatalf("the timeout was not honoured: %v", elapsed)
	}

	close(slow)

	fast := time.Now()
	deps.NativeCopy = func(text string) error { return nil }
	if route := Copy("prompt", deps); route != RouteNative {
		t.Fatalf("a fast copy must report the native route, got %q", route)
	}
	if time.Since(fast) > NativeTimeout {
		t.Fatalf("fast copies must not wait for the timeout")
	}
}

func TestSequenceEncoding(t *testing.T) {
	sequence := Sequence("café")
	if !strings.HasPrefix(sequence, "\x1b]52;c;") || !strings.HasSuffix(sequence, "\x07") {
		t.Fatalf("unexpected OSC 52 sequence: %q", sequence)
	}
	want := "\x1b]52;c;" + base64.StdEncoding.EncodeToString([]byte("café")) + "\x07"
	if sequence != want {
		t.Fatalf("payload must be base64 of the UTF-8 text: %q", sequence)
	}
}
