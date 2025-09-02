"""Tests for documentation examples and validation.

This module tests the code examples provided in the README and other documentation
to ensure they work correctly and remain accurate.
"""

import os
import tempfile
import shutil
from pathlib import Path
from click.testing import CliRunner
from promptcraft.main import promptcraft


class TestREADMEExamples:
    """Test examples from README.md to ensure accuracy."""
    
    def test_basic_cli_commands(self):
        """Test basic CLI command examples work as documented."""
        runner = CliRunner()
        
        # Test --version command
        result = runner.invoke(promptcraft, ["--version"])
        assert result.exit_code == 0
        assert "PromptCraft" in result.output
        
        # Test --help command
        result = runner.invoke(promptcraft, ["--help"])
        assert result.exit_code == 0
        assert "PromptCraft CLI" in result.output
        
        # Test --list command (should work even with no templates)
        result = runner.invoke(promptcraft, ["--list"])
        assert result.exit_code == 0
    
    def test_init_command_creates_structure(self):
        """Test --init command creates documented directory structure."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            
            # Test --init command
            result = runner.invoke(promptcraft, ["--init"])
            assert result.exit_code == 0
            
            # Verify documented structure is created
            promptcraft_dir = Path(".promptcraft")
            commands_dir = promptcraft_dir / "commands"
            
            assert promptcraft_dir.exists()
            assert commands_dir.exists()
            assert (commands_dir / "exemplo.md").exists()
    
    def test_template_execution_examples(self):
        """Test template execution examples from README."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            
            # Initialize project
            result = runner.invoke(promptcraft, ["--init"])
            assert result.exit_code == 0
            
            # Test basic template execution with --stdout
            result = runner.invoke(promptcraft, ["exemplo", "World", "--stdout"])
            assert result.exit_code == 0
            assert "World" in result.output
            
            # Test execution with leading slash
            result = runner.invoke(promptcraft, ["/exemplo", "Test", "--stdout"])
            assert result.exit_code == 0
            assert "Test" in result.output
    
    def test_template_discovery_paths(self):
        """Test that documented template discovery paths work."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            
            # Create local template
            local_dir = Path(".promptcraft/commands")
            local_dir.mkdir(parents=True)
            (local_dir / "local-test.md").write_text(
                "Local test template\nLocal: $ARGUMENTS[0]"
            )
            
            # Test that local template is discovered
            result = runner.invoke(promptcraft, ["--list"])
            assert result.exit_code == 0
            assert "local-test" in result.output
            
            # Test local template execution
            result = runner.invoke(promptcraft, ["local-test", "value", "--stdout"])
            assert result.exit_code == 0
            assert "Local: value" in result.output


class TestTemplateFormat:
    """Test template format specifications from documentation."""
    
    def test_template_file_requirements(self):
        """Test documented template file requirements."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            
            # Create template following documented format
            template_dir = Path(".promptcraft/commands")
            template_dir.mkdir(parents=True)
            
            template_content = """Simple greeting template
Hello $ARGUMENTS[0]! Welcome to PromptCraft."""
            
            (template_dir / "hello.md").write_text(template_content)
            
            # Test template discovery
            result = runner.invoke(promptcraft, ["--list"])
            assert result.exit_code == 0
            assert "hello" in result.output
            assert "Simple greeting template" in result.output
            
            # Test template execution matches documented output
            result = runner.invoke(promptcraft, ["hello", "World", "--stdout"])
            assert result.exit_code == 0
            assert "Hello World! Welcome to PromptCraft." in result.output
    
    def test_complex_template_example(self):
        """Test complex template example from documentation."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            
            template_dir = Path(".promptcraft/commands")
            template_dir.mkdir(parents=True)
            
            # Create complex template from README
            complex_template = """Generate comprehensive user story with acceptance criteria
## User Story: $ARGUMENTS[0]

**As a** $ARGUMENTS[1],
**I want** $ARGUMENTS[2],
**so that** $ARGUMENTS[3].

### Acceptance Criteria
1. $ARGUMENTS[4]
2. All edge cases are handled appropriately
3. Performance requirements are met
4. Security considerations are addressed

### Technical Notes
- Component: $ARGUMENTS[0]
- Priority: High
- Estimated effort: TBD"""
            
            (template_dir / "user-story.md").write_text(complex_template)
            
            # Test complex template execution
            args = [
                "user-story",
                "Authentication",
                "developer", 
                "secure login system",
                "users can access protected resources",
                "Login form validates credentials",
                "--stdout"
            ]
            
            result = runner.invoke(promptcraft, args)
            assert result.exit_code == 0
            assert "Authentication" in result.output
            assert "developer" in result.output
            assert "secure login system" in result.output
            assert "Login form validates credentials" in result.output


class TestErrorHandlingDocumentation:
    """Test documented error handling scenarios."""
    
    def test_command_not_found_error(self):
        """Test documented command not found error message."""
        runner = CliRunner()
        
        result = runner.invoke(promptcraft, ["nonexistent-command"])
        assert result.exit_code == 1
        assert "Command '/nonexistent-command' not found" in result.output
        assert "Run 'promptcraft --list' to see available commands" in result.output
    
    def test_missing_command_name_error(self):
        """Test documented missing command name error."""
        runner = CliRunner()
        
        result = runner.invoke(promptcraft, [])
        assert result.exit_code == 1
        assert "Command name is required" in result.output
        assert "Use 'promptcraft --help' for usage information" in result.output


class TestPlatformSpecificExamples:
    """Test platform-specific examples work correctly."""
    
    def test_argument_with_spaces_handling(self):
        """Test documented argument handling for arguments with spaces."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            
            # Initialize and create test template
            result = runner.invoke(promptcraft, ["--init"])
            assert result.exit_code == 0
            
            # Test argument with spaces (documented requirement)
            result = runner.invoke(promptcraft, ["exemplo", "argument with spaces", "--stdout"])
            assert result.exit_code == 0
            assert "argument with spaces" in result.output
    
    def test_stdout_flag_behavior(self):
        """Test --stdout flag behavior as documented."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            
            # Initialize project
            result = runner.invoke(promptcraft, ["--init"])
            assert result.exit_code == 0
            
            # Test --stdout flag produces terminal output
            result = runner.invoke(promptcraft, ["exemplo", "test", "--stdout"])
            assert result.exit_code == 0
            assert "Prompt for '/exemplo' generated:" in result.output
            assert "test" in result.output
            
            # Test without --stdout (should try clipboard but show success message)
            result = runner.invoke(promptcraft, ["exemplo", "test2"])
            # Exit code depends on clipboard availability, but should show appropriate message
            assert ("copied to clipboard" in result.output or 
                    "Clipboard unavailable" in result.output)


class TestTemplateOrganizationExamples:
    """Test template organization examples from documentation."""
    
    def test_template_naming_conventions(self):
        """Test that documented naming conventions work correctly."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            
            template_dir = Path(".promptcraft/commands")
            template_dir.mkdir(parents=True)
            
            # Test recommended naming convention
            good_names = ["user-story.md", "bug-report.md", "api-documentation.md"]
            
            for name in good_names:
                (template_dir / name).write_text(f"Test template for {name}\nContent for {name}")
            
            # Test discovery of properly named templates
            result = runner.invoke(promptcraft, ["--list"])
            assert result.exit_code == 0
            
            # Verify all templates are discovered with correct names
            for name in good_names:
                template_name = name.replace(".md", "")
                assert template_name in result.output
    
    def test_template_subdirectory_handling(self):
        """Test template organization in subdirectories (mentioned in troubleshooting)."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            
            # Create template structure with subdirectories
            template_dir = Path(".promptcraft/commands")
            archive_dir = template_dir / "archive"
            archive_dir.mkdir(parents=True)
            
            # Main template
            (template_dir / "active-template.md").write_text("Active template\nActive content")
            
            # Archived template (should not interfere)
            (archive_dir / "old-template.md").write_text("Old template\nOld content")
            
            # Test that main template is discovered
            result = runner.invoke(promptcraft, ["--list"])
            assert result.exit_code == 0
            assert "active-template" in result.output
            
            # Test template execution
            result = runner.invoke(promptcraft, ["active-template", "--stdout"])
            assert result.exit_code == 0
            assert "Active content" in result.output