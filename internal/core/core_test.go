package core

import (
	"errors"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/quantmind-br/promptcraft/internal/apperror"
)

func newTestProcessor(t *testing.T, projectDir, userDir string) *Processor {
	t.Helper()
	if err := os.MkdirAll(projectDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(userDir, 0o755); err != nil {
		t.Fatal(err)
	}
	return &Processor{
		Cwd:            func() (string, error) { return projectDir, nil },
		Home:           func() (string, error) { return userDir, nil },
		Now:            time.Now,
		pathCache:      map[string]pathEntry{},
		discoveryCache: map[string]discoveryEntry{},
	}
}

func writeTemplate(t *testing.T, path, content string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
}

func TestFindCommandPathSearchesProjectBeforeUser(t *testing.T) {
	root := t.TempDir()
	project := filepath.Join(root, "project")
	user := filepath.Join(root, "user")
	processor := newTestProcessor(t, project, user)

	writeTemplate(t, filepath.Join(user, ".promptcraft", "commands", "shared.md"), "user copy")

	found, err := processor.FindCommandPath("shared")
	if err != nil {
		t.Fatal(err)
	}
	if found != filepath.Join(user, ".promptcraft", "commands", "shared.md") {
		t.Fatalf("the user template is the only one present, got %s", found)
	}

	// Once a project template exists it wins over the user copy.
	writeTemplate(t, filepath.Join(project, ".promptcraft", "commands", "shared.md"), "project copy")
	processor.InvalidateCaches()

	found, err = processor.FindCommandPath("shared")
	if err != nil {
		t.Fatal(err)
	}
	if found != filepath.Join(project, ".promptcraft", "commands", "shared.md") {
		t.Fatalf("project template must win over the user template, got %s", found)
	}
}

func TestFindCommandPathOnlyInUserScope(t *testing.T) {
	root := t.TempDir()
	processor := newTestProcessor(t, filepath.Join(root, "project"), filepath.Join(root, "user"))
	writeTemplate(t, filepath.Join(root, "user", ".promptcraft", "commands", "only-user.md"), "content")

	found, err := processor.FindCommandPath("only-user")
	if err != nil {
		t.Fatal(err)
	}
	if found != filepath.Join(root, "user", ".promptcraft", "commands", "only-user.md") {
		t.Fatalf("unexpected path %s", found)
	}
}

func TestFindCommandPathMissing(t *testing.T) {
	root := t.TempDir()
	processor := newTestProcessor(t, filepath.Join(root, "project"), filepath.Join(root, "user"))

	_, err := processor.FindCommandPath("missing")
	var perr *apperror.Error
	if !errors.As(err, &perr) || perr.Code() != apperror.CodeCommandNotFound {
		t.Fatalf("expected CommandNotFoundError, got %v", err)
	}
	expected := "Command 'missing' not found. Searched in: " + processor.ProjectDir() + ", " + processor.UserDir()
	if perr.Message != expected {
		t.Fatalf("message mismatch:\n got %q\nwant %q", perr.Message, expected)
	}

	_, err = processor.FindCommandPath("")
	if !errors.As(err, &perr) || perr.Message != "Command name must be a non-empty string" {
		t.Fatalf("empty name must report the same message, got %v", err)
	}
}

func TestPathCacheKeepsHitsAndMisses(t *testing.T) {
	root := t.TempDir()
	project := filepath.Join(root, "project")
	user := filepath.Join(root, "user")
	processor := newTestProcessor(t, project, user)

	now := time.Unix(1700000000, 0)
	processor.Now = func() time.Time { return now }

	// A miss is cached: the same lookup fails inside the TTL even after the
	// file appears, and succeeds once the entry expires.
	_, err := processor.FindCommandPath("ghost")
	if err == nil {
		t.Fatal("expected a miss")
	}
	key := project + "\x00" + user + "\x00ghost"
	entry, ok := processor.pathCache[key]
	if !ok || entry.path != "" {
		t.Fatalf("miss was not cached: %+v", processor.pathCache)
	}

	writeTemplate(t, filepath.Join(project, ".promptcraft", "commands", "ghost.md"), "late")
	if _, err := processor.FindCommandPath("ghost"); err == nil {
		t.Fatal("the cached miss must still be served inside the TTL window")
	}

	now = now.Add(PathCacheTTL + time.Second)
	found, err := processor.FindCommandPath("ghost")
	if err != nil {
		t.Fatalf("expired cache must be re-resolved: %v", err)
	}
	if found != filepath.Join(project, ".promptcraft", "commands", "ghost.md") {
		t.Fatalf("unexpected path after expiry: %s", found)
	}

	// A cached hit is verified on disk before it is returned.
	writeTemplate(t, filepath.Join(project, ".promptcraft", "commands", "hit.md"), "x")
	found, err = processor.FindCommandPath("hit")
	if err != nil {
		t.Fatal(err)
	}
	if entry := processor.pathCache[project+"\x00"+user+"\x00hit"]; entry.path != found {
		t.Fatalf("hit was not cached: %+v", entry)
	}
	if err := os.Remove(found); err != nil {
		t.Fatal(err)
	}
	if _, err := processor.FindCommandPath("hit"); err == nil {
		t.Fatal("a stale cached hit must be re-resolved")
	}
}

func TestGeneratePromptSubstitutesArguments(t *testing.T) {
	root := t.TempDir()
	path := filepath.Join(root, "template.md")
	writeTemplate(t, path, "Hello $ARGUMENTS\nSecond: $ARGUMENTS[1]\nExtra: $ARGUMENTS[3]\n")

	result, err := (&Processor{}).GeneratePrompt(path, []string{"one", "two"})
	if err != nil {
		t.Fatal(err)
	}
	want := "Hello one two\nSecond: two\nExtra: \n"
	if result != want {
		t.Fatalf("got %q want %q", result, want)
	}

	result, err = (&Processor{}).GeneratePrompt(path, nil)
	if err != nil {
		t.Fatal(err)
	}
	if result != "Hello \nSecond: \nExtra: \n" {
		t.Fatalf("empty arguments must produce empty substitutions, got %q", result)
	}
}

func TestGeneratePromptReadErrors(t *testing.T) {
	root := t.TempDir()
	processor := &Processor{}

	_, err := processor.GeneratePrompt(filepath.Join(root, "absent.md"), nil)
	var perr *apperror.Error
	if !errors.As(err, &perr) || perr.Code() != apperror.CodeTemplateFileNotFound {
		t.Fatalf("expected TEMPLATE_FILE_NOT_FOUND, got %v", err)
	}

	binary := filepath.Join(root, "binary.md")
	writeTemplate(t, binary, "text\x00bytes")
	_, err = processor.GeneratePrompt(binary, nil)
	if !errors.As(err, &perr) || perr.Code() != apperror.CodeTemplateEncoding {
		t.Fatalf("binary content must report TEMPLATE_ENCODING_ERROR, got %v", err)
	}

	invalidUTF8 := filepath.Join(root, "invalid.md")
	if err := os.WriteFile(invalidUTF8, []byte{0xff, 0xfe}, 0o644); err != nil {
		t.Fatal(err)
	}
	_, err = processor.GeneratePrompt(invalidUTF8, nil)
	if !errors.As(err, &perr) || perr.Code() != apperror.CodeTemplateEncoding {
		t.Fatalf("invalid UTF-8 must report TEMPLATE_ENCODING_ERROR, got %v", err)
	}

	directory := filepath.Join(root, "dir.md")
	if err := os.MkdirAll(directory, 0o755); err != nil {
		t.Fatal(err)
	}
	_, err = processor.GeneratePrompt(directory, nil)
	if !errors.As(err, &perr) || perr.Code() != apperror.CodeTemplateIO {
		t.Fatalf("directory read must report TEMPLATE_IO_ERROR, got %v", err)
	}
}

func TestProcessCommandWrapsErrorsWithContext(t *testing.T) {
	root := t.TempDir()
	processor := newTestProcessor(t, filepath.Join(root, "project"), filepath.Join(root, "user"))

	_, err := processor.ProcessCommand("nope", []string{"a"})
	if err == nil || err.Error() != "Command 'nope' processing failed: "+notFoundMessage(processor, "nope") {
		t.Fatalf("unexpected wrapped error: %v", err)
	}

	binary := filepath.Join(root, "project", ".promptcraft", "commands", "bad.md")
	writeTemplate(t, binary, "ok\x00")
	_, err = processor.ProcessCommand("bad", nil)
	var perr *apperror.Error
	if !errors.As(err, &perr) || perr.Code() != apperror.CodeTemplateEncoding {
		t.Fatalf("expected encoding error code preserved, got %v", err)
	}
	if err.Error() != "Command 'bad' template processing failed: Failed to decode template file "+binary+": binary content detected" {
		t.Fatalf("wrapped message mismatch: %v", err)
	}
}

func TestProcessTemplateRejectsEmptyContent(t *testing.T) {
	processor := &Processor{}
	if _, err := processor.ProcessTemplate("   \n"); err == nil {
		t.Fatal("empty content must fail")
	}
	got, err := processor.ProcessTemplate("content")
	if err != nil || got != "content" {
		t.Fatalf("content must pass through unchanged: %q / %v", got, err)
	}
}

func TestExtractDescription(t *testing.T) {
	root := t.TempDir()
	cases := []struct {
		content string
		want    string
	}{
		{"# Title\nbody", "Title"},
		{"   \n  plain line  \n", "plain line"},
		{"###### Six", "Six"},
		{"####### Too Many", "###### Too Many"},
		{"## No space", "No space"},
		{"# ", "No description available"},
		{"", "No description available"},
	}

	for _, testCase := range cases {
		path := filepath.Join(root, "case.md")
		writeTemplate(t, path, testCase.content)
		if got := ExtractDescription(path); got != testCase.want {
			t.Fatalf("content %q: got %q want %q", testCase.content, got, testCase.want)
		}
	}

	if got := ExtractDescription(filepath.Join(root, "absent.md")); got != "No description available" {
		t.Fatalf("unreadable file must fall back, got %q", got)
	}
}

func TestDiscoverCommandsSkipsUnreadableAndNonMarkdown(t *testing.T) {
	root := t.TempDir()
	project := filepath.Join(root, "project")
	user := filepath.Join(root, "user")
	processor := newTestProcessor(t, project, user)

	writeTemplate(t, filepath.Join(project, ".promptcraft", "commands", "ok.md"), "# Ok")
	writeTemplate(t, filepath.Join(project, ".promptcraft", "commands", "ignored.txt"), "not a template")
	if err := os.MkdirAll(filepath.Join(project, ".promptcraft", "commands", "sub.md"), 0o755); err != nil {
		t.Fatal(err)
	}

	got := processor.DiscoverCommands()
	if len(got) != 1 || got[0].Name != "ok" || got[0].Source != SourceProject {
		t.Fatalf("only markdown files inside the search directory count: %+v", got)
	}

	// A missing search directory contributes nothing.
	empty := newTestProcessor(t, filepath.Join(root, "absent-project"), filepath.Join(root, "absent-user"))
	if len(empty.DiscoverCommands()) != 0 {
		t.Fatal("missing directories must be skipped")
	}
}

func TestListTemplatesKeepsProjectOnNameConflict(t *testing.T) {
	root := t.TempDir()
	project := filepath.Join(root, "project")
	user := filepath.Join(root, "user")
	processor := newTestProcessor(t, project, user)

	writeTemplate(t, filepath.Join(project, ".promptcraft", "commands", "same.md"), "# Project copy")
	writeTemplate(t, filepath.Join(user, ".promptcraft", "commands", "same.md"), "# User copy")

	templates := processor.ListTemplates()
	if len(templates) != 1 {
		t.Fatalf("duplicate names must collapse to one row, got %d", len(templates))
	}
	if templates[0].Source != SourceProject || templates[0].Scope() != ScopeProject {
		t.Fatalf("project template must win: %+v", templates[0])
	}
}

func TestInitProjectIsIdempotentAndNeverOverwrites(t *testing.T) {
	root := t.TempDir()
	project := filepath.Join(root, "project")
	processor := newTestProcessor(t, project, filepath.Join(root, "user"))

	result := processor.InitProject()
	if result.Error != "" {
		t.Fatal(result.Error)
	}
	if len(result.Created) != 2 || result.Created[0] != "Created directory: .promptcraft/commands/" {
		t.Fatalf("unexpected first init result: %+v", result)
	}

	writeTemplate(t, filepath.Join(project, ".promptcraft", "commands", "exemplo.md"), "custom content")
	result = processor.InitProject()
	if len(result.Created) != 0 || len(result.Existing) != 2 {
		t.Fatalf("second init must report existing items only: %+v", result)
	}
	content, err := os.ReadFile(filepath.Join(project, ".promptcraft", "commands", "exemplo.md"))
	if err != nil {
		t.Fatal(err)
	}
	if string(content) != "custom content" {
		t.Fatalf("existing template must not be overwritten, got %q", content)
	}

	if ExampleTemplate == "" {
		t.Fatal("embedded example template is empty")
	}
}

func TestSaveAndDeleteTemplateGuards(t *testing.T) {
	root := t.TempDir()
	project := filepath.Join(root, "project")
	user := filepath.Join(root, "user")
	processor := newTestProcessor(t, project, user)

	if _, err := processor.SaveTemplate("bad name/", ScopeProject, "content"); err == nil {
		t.Fatal("path separators must be refused")
	}
	if _, err := processor.SaveTemplate(".hidden", ScopeProject, "content"); err == nil {
		t.Fatal("dot-prefixed names must be refused")
	}
	if _, err := processor.SaveTemplate("", ScopeProject, "content"); err == nil {
		t.Fatal("empty names must be refused")
	}
	if _, err := processor.SaveTemplate("ok", "unknown", "content"); err == nil || err.Error() != "Unknown scope: unknown" {
		t.Fatalf("unknown scope must fail: %v", err)
	}

	// Populate the caches so invalidation can be observed.
	processor.DiscoverCommands()
	_, err := processor.FindCommandPath("ok")
	if err == nil {
		t.Fatal("the path cache must record the miss before saving")
	}

	path, err := processor.SaveTemplate("typed.md", ScopeUser, "body")
	if err != nil {
		t.Fatal(err)
	}
	if path != filepath.Join(user, ".promptcraft", "commands", "typed.md") {
		t.Fatalf("trailing .md must be stripped: %s", path)
	}
	if len(processor.pathCache) != 0 || len(processor.discoveryCache) != 0 {
		t.Fatal("save must invalidate the caches")
	}

	outside := filepath.Join(root, "outside.md")
	writeTemplate(t, outside, "not a template")
	if err := processor.DeleteTemplate(outside); err == nil {
		t.Fatal("deleting outside the template directories must be refused")
	}

	directory := filepath.Join(project, ".promptcraft", "commands", "adir.md")
	if err := os.MkdirAll(directory, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := processor.DeleteTemplate(directory); err == nil || err.Error() != "Cannot delete directory: "+directory {
		t.Fatalf("directories must be refused: %v", err)
	}

	if err := processor.DeleteTemplate(path); err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(path); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("template must be removed, got %v", err)
	}

	if err := processor.DeleteTemplate(path); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("missing file must report ErrNotExist, got %v", err)
	}
}

func TestNormalizeAndValidateName(t *testing.T) {
	if got := NormalizeName("  typed.md  "); got != "typed" {
		t.Fatalf("normalization failed: %q", got)
	}
	if got := NormalizeName("TYPED.MD"); got != "TYPED" {
		t.Fatalf("case-insensitive .md suffix must be stripped: %q", got)
	}

	cases := []struct {
		name string
		want string
	}{
		{"", "Name is required."},
		{"a/b", "Name cannot contain path separators ('/' or '\\'). Use a single word or use hyphens."},
		{"a\\b", "Name cannot contain path separators ('/' or '\\'). Use a single word or use hyphens."},
		{".hidden", "Name cannot start with a dot."},
		{"valid-name", ""},
	}
	for _, testCase := range cases {
		if got := ValidateName(testCase.name); got != testCase.want {
			t.Fatalf("name %q: got %q want %q", testCase.name, got, testCase.want)
		}
	}
}
