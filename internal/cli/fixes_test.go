package cli

import (
	"errors"
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// failingWriter reports a delivery failure so the exit code must reflect it.
type failingWriter struct{}

func (failingWriter) Write([]byte) (int, error) { return 0, errors.New("broken pipe") }

func TestInitFailureExitsWithCodeOne(t *testing.T) {
	options, buffer := testOptions(t)

	// An ordinary file cannot be a working-directory root on any platform.
	blocked := filepath.Join(t.TempDir(), "blocked")
	if err := os.WriteFile(blocked, []byte("not a directory"), 0o644); err != nil {
		t.Fatal(err)
	}
	options.Core.Cwd = func() (string, error) { return blocked, nil }

	code := Run([]string{"--init"}, options)
	if code == 0 {
		t.Fatalf("a failed initialization must not exit 0: output=%q", buffer.String())
	}
	if !strings.Contains(buffer.String(), "❌") {
		t.Fatalf("the failure must be reported: %q", buffer.String())
	}

}

func TestWriteFailureIsReportedAsAFailedRun(t *testing.T) {
	options, _ := testOptions(t)
	writeTemplate(t, filepath.Join(options.Core.ProjectDir(), "greet.md"), "hello $ARGUMENTS")

	options.Out = failingWriter{}
	options.Color = false
	if code := Run([]string{"--stdout", "greet", "world"}, options); code != 1 {
		t.Fatalf("a broken pipe must exit 1, got %d", code)
	}

	// A writer that works still reports success.
	options.Out = io.Discard
	if code := Run([]string{"--stdout", "greet", "world"}, options); code != 0 {
		t.Fatalf("a successful run must exit 0, got %d", code)
	}
}
