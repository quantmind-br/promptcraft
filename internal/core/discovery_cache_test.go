package core

import (
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestDiscoverCommandsCachesUntilDirectoryChanges(t *testing.T) {
	root := t.TempDir()
	project := filepath.Join(root, "project")
	user := filepath.Join(root, "user")
	processor := newTestProcessor(t, project, user)

	writeTemplate(t, filepath.Join(project, ".promptcraft", "commands", "beta.md"), "# Beta")
	writeTemplate(t, filepath.Join(user, ".promptcraft", "commands", "alpha.md"), "# Alpha")

	first := processor.DiscoverCommands()
	if len(first) != 2 || first[0].Name != "alpha" {
		t.Fatalf("case-insensitive ordering failed: %+v", first)
	}

	// Changing a file does not change the directory mtime, so the cached
	// snapshot is still served inside the TTL window.
	writeTemplate(t, filepath.Join(user, ".promptcraft", "commands", "alpha.md"), "# Changed")
	cached := processor.DiscoverCommands()
	if len(cached) != 2 || cached[0].Description != "Alpha" {
		t.Fatalf("cache should serve the recorded snapshot: %+v", cached)
	}

	// Touching the directory invalidates it.
	if err := os.Chtimes(filepath.Join(project, ".promptcraft", "commands"), time.Now().Add(time.Second), time.Now().Add(2*time.Second)); err != nil {
		t.Fatal(err)
	}
	refreshed := processor.DiscoverCommands()
	if len(refreshed) != 2 || refreshed[0].Description != "Changed" {
		t.Fatalf("cache must be refreshed after a directory change: %+v", refreshed)
	}

	processor.InvalidateCaches()
	writeTemplate(t, filepath.Join(project, ".promptcraft", "commands", "gamma.md"), "# Gamma")
	if got := processor.DiscoverCommands(); len(got) != 3 {
		t.Fatalf("explicit invalidation must rescan, got %d entries", len(got))
	}

	// TTL expiry rescans even without a directory change.
	processor.Now = func() time.Time { return time.Now().Add(DiscoveryCacheTTL + time.Second) }
	writeTemplate(t, filepath.Join(user, ".promptcraft", "commands", "alpha.md"), "# After TTL")
	if got := processor.DiscoverCommands(); len(got) != 3 || got[0].Description != "After TTL" {
		t.Fatalf("expired discovery cache must rescan: %+v", got)
	}
}
