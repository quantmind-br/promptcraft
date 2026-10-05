package clipboard

import (
	"os"
	"path/filepath"
	"testing"
)

func TestDefaultWiresTheProcessEnvironmentAndBackends(t *testing.T) {
	t.Setenv("PROMPTCRAFT_TEST_MARKER", "value")

	deps := Default()
	if deps.Env["PROMPTCRAFT_TEST_MARKER"] != "value" {
		t.Fatalf("the environment snapshot is incomplete: %+v", deps.Env)
	}
	if deps.NativeCopy == nil || deps.OSC52Writer == nil || deps.FileExists == nil {
		t.Fatal("Default must wire every backend")
	}
	if deps.TTYPath != "/dev/tty" {
		t.Fatalf("unexpected tty path: %s", deps.TTYPath)
	}
	if !deps.FileExists(os.TempDir()) {
		t.Fatal("FileExists must resolve real paths")
	}
}

func TestWriteToTTYUsesTheInjectedPath(t *testing.T) {
	path := filepath.Join(t.TempDir(), "tty")
	deps := Deps{Env: map[string]string{}, TTYPath: path}

	if err := WriteToTTY(deps, "café"); err != nil {
		t.Fatal(err)
	}

	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if string(data) != Sequence("café") {
		t.Fatalf("sequence was not written: %q", string(data))
	}
}

func TestCopyFallsBackToTheDefaultWriterWhenNoneIsInjected(t *testing.T) {
	path := filepath.Join(t.TempDir(), "tty")
	deps := Deps{Env: map[string]string{"PROMPTCRAFT_CLIPBOARD": "osc52"}, TTYPath: path}

	if route := Copy("prompt", deps); route != RouteOSC52 {
		t.Fatalf("expected the default writer to carry the copy, got %q", route)
	}

	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if string(data) != Sequence("prompt") {
		t.Fatalf("unexpected payload: %q", string(data))
	}
}

func TestNativeCopyWithoutABackendReportsNothing(t *testing.T) {
	deps := testDeps(map[string]string{"DISPLAY": ":0", "X11_SOCKET": "yes"})
	if route := Copy("prompt", deps); route != "" {
		t.Fatalf("a nil native backend must not report a route, got %q", route)
	}
}
