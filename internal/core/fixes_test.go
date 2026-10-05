package core

import (
	"errors"
	"os"
	"path/filepath"
	"testing"

	"github.com/quantmind-br/promptcraft/internal/apperror"
)

func TestCommandNameCannotEscapeTheTemplateRoot(t *testing.T) {
	root := t.TempDir()
	project := filepath.Join(root, "project")
	user := filepath.Join(root, "user")
	processor := newTestProcessor(t, project, user)

	// A file outside both roots exists but must never be reachable by name.
	outside := filepath.Join(root, "secret.md")
	writeTemplate(t, outside, "must not be read")

	_, err := processor.FindCommandPath("../secret")
	var perr *apperror.Error
	if !errors.As(err, &perr) || perr.Code() != apperror.CodeCommandNotFound {
		t.Fatalf("a traversal name must be refused: %v", err)
	}
}

func TestDeleteTemplateRefusesSymlinkedRoots(t *testing.T) {
	root := t.TempDir()
	project := filepath.Join(root, "project")
	user := filepath.Join(root, "user")
	if err := os.MkdirAll(project, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(user, 0o755); err != nil {
		t.Fatal(err)
	}

	external := filepath.Join(root, "external")
	if err := os.MkdirAll(filepath.Join(external, ".promptcraft", "commands"), 0o755); err != nil {
		t.Fatal(err)
	}
	victim := filepath.Join(external, ".promptcraft", "commands", "victim.md")
	writeTemplate(t, victim, "outside the template roots")

	if err := os.Symlink(filepath.Join(external, ".promptcraft", "commands"), filepath.Join(project, ".promptcraft")); err != nil {
		t.Skipf("symlinks are not supported here: %v", err)
	}

	processor := &Processor{
		Cwd:  func() (string, error) { return project, nil },
		Home: func() (string, error) { return user, nil },
	}

	if err := processor.DeleteTemplate(victim); err == nil {
		t.Fatal("a symlinked template directory must not authorize deleting an external file")
	}
	if _, err := os.Stat(victim); err != nil {
		t.Fatalf("the external file must survive: %v", err)
	}
}

func TestDeleteTemplateRefusesSymlinkedFiles(t *testing.T) {
	root := t.TempDir()
	project := filepath.Join(root, "project")
	user := filepath.Join(root, "user")
	processor := newTestProcessor(t, project, user)

	external := filepath.Join(root, "external.txt")
	writeTemplate(t, external, "outside the template roots")

	link := filepath.Join(processor.ProjectDir(), "link.md")
	if err := os.Symlink(external, link); err != nil {
		t.Skipf("symlinks are not supported here: %v", err)
	}

	if err := processor.DeleteTemplate(link); err == nil {
		t.Fatal("a symlinked template must not authorize deleting the external target")
	}
	if _, err := os.Stat(external); err != nil {
		t.Fatalf("the external file must survive: %v", err)
	}
}

func TestProjectPrecedenceSurvivesACachedUserHit(t *testing.T) {
	root := t.TempDir()
	project := filepath.Join(root, "project")
	user := filepath.Join(root, "user")
	processor := newTestProcessor(t, project, user)

	writeTemplate(t, filepath.Join(user, ".promptcraft", "commands", "shared.md"), "# User")
	if _, err := processor.FindCommandPath("shared"); err != nil {
		t.Fatal(err)
	}

	// A project template created later must win even while the cache is valid.
	writeTemplate(t, filepath.Join(project, ".promptcraft", "commands", "shared.md"), "# Project")
	found, err := processor.FindCommandPath("shared")
	if err != nil {
		t.Fatal(err)
	}
	if found != filepath.Join(project, ".promptcraft", "commands", "shared.md") {
		t.Fatalf("project precedence must be re-checked before a cached user hit: %s", found)
	}
}
