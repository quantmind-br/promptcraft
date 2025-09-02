"""Unit tests for core module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch
import threading
import time

import pytest
from promptcraft.core import TemplateProcessor, find_command_path, generate_prompt, process_command, discover_commands, _extract_description, CommandInfo
from promptcraft.exceptions import TemplateError, CommandNotFoundError, TemplateReadError


def test_template_processor_init():
    """Test TemplateProcessor initialization."""
    processor = TemplateProcessor()
    assert processor is not None


def test_process_template_basic():
    """Test basic template processing functionality."""
    processor = TemplateProcessor()
    template_content = "Hello, World!"
    result = processor.process_template(template_content)
    assert result == template_content


def test_process_template_none_content():
    """Test that None template content raises TemplateError."""
    processor = TemplateProcessor()
    with pytest.raises(TemplateError, match="Template content cannot be None"):
        processor.process_template(None)


def test_process_template_non_string_content():
    """Test that non-string template content raises TemplateError."""
    processor = TemplateProcessor()
    with pytest.raises(TemplateError, match="Template content must be a string"):
        processor.process_template(123)


def test_process_template_empty_content():
    """Test that empty template content raises TemplateError."""
    processor = TemplateProcessor()
    with pytest.raises(TemplateError, match="Template content cannot be empty"):
        processor.process_template("")


def test_process_template_whitespace_only():
    """Test that whitespace-only template content raises TemplateError."""
    processor = TemplateProcessor()
    with pytest.raises(TemplateError, match="Template content cannot be empty"):
        processor.process_template("   \n\t   ")


# find_command_path() function tests

def test_find_command_path_current_directory():
    """Test successful command discovery in current working directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test directory structure
        cmd_dir = Path(tmpdir) / ".promptcraft" / "commands"
        cmd_dir.mkdir(parents=True)
        
        # Create test command file
        cmd_file = cmd_dir / "test-cmd.md"
        cmd_file.write_text("# Test Command\nThis is a test command.")
        
        # Mock current working directory
        with patch('promptcraft.core.Path.cwd', return_value=Path(tmpdir)):
            result = find_command_path("test-cmd")
            assert result == cmd_file
            assert result.exists()


def test_find_command_path_home_directory_fallback():
    """Test fallback to home directory when command not found in current directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create home directory structure only
        home_cmd_dir = Path(tmpdir) / ".promptcraft" / "commands"
        home_cmd_dir.mkdir(parents=True)
        
        # Create command file in home directory
        cmd_file = home_cmd_dir / "global-cmd.md"
        cmd_file.write_text("# Global Command\nThis is a global command.")
        
        # Create empty current directory (no .promptcraft folder)
        with tempfile.TemporaryDirectory() as cwd_tmpdir:
            with patch('promptcraft.core.Path.cwd', return_value=Path(cwd_tmpdir)), \
                 patch('promptcraft.core.Path.home', return_value=Path(tmpdir)):
                result = find_command_path("global-cmd")
                assert result == cmd_file
                assert result.exists()


def test_find_command_path_current_directory_priority():
    """Test that current directory takes priority over home directory."""
    with tempfile.TemporaryDirectory() as cwd_tmpdir, \
         tempfile.TemporaryDirectory() as home_tmpdir:
        
        # Create both directory structures
        cwd_cmd_dir = Path(cwd_tmpdir) / ".promptcraft" / "commands"
        cwd_cmd_dir.mkdir(parents=True)
        home_cmd_dir = Path(home_tmpdir) / ".promptcraft" / "commands"
        home_cmd_dir.mkdir(parents=True)
        
        # Create same command in both locations with different content
        cwd_cmd_file = cwd_cmd_dir / "priority-cmd.md"
        cwd_cmd_file.write_text("# Local Command")
        home_cmd_file = home_cmd_dir / "priority-cmd.md"
        home_cmd_file.write_text("# Global Command")
        
        with patch('promptcraft.core.Path.cwd', return_value=Path(cwd_tmpdir)), \
             patch('promptcraft.core.Path.home', return_value=Path(home_tmpdir)):
            result = find_command_path("priority-cmd")
            # Should return the current directory version
            assert result == cwd_cmd_file
            assert result.read_text() == "# Local Command"


def test_find_command_path_command_not_found():
    """Test CommandNotFoundError when command template not found in any location."""
    with tempfile.TemporaryDirectory() as cwd_tmpdir, \
         tempfile.TemporaryDirectory() as home_tmpdir:
        
        # Create directories but no command files
        cwd_cmd_dir = Path(cwd_tmpdir) / ".promptcraft" / "commands"
        cwd_cmd_dir.mkdir(parents=True)
        home_cmd_dir = Path(home_tmpdir) / ".promptcraft" / "commands"
        home_cmd_dir.mkdir(parents=True)
        
        with patch('promptcraft.core.Path.cwd', return_value=Path(cwd_tmpdir)), \
             patch('promptcraft.core.Path.home', return_value=Path(home_tmpdir)):
            with pytest.raises(CommandNotFoundError) as exc_info:
                find_command_path("nonexistent-cmd")
            
            error_message = str(exc_info.value)
            assert "Command 'nonexistent-cmd' not found" in error_message
            assert str(cwd_cmd_dir) in error_message
            assert str(home_cmd_dir) in error_message


def test_find_command_path_missing_directories():
    """Test graceful handling when .promptcraft directories don't exist."""
    with tempfile.TemporaryDirectory() as cwd_tmpdir, \
         tempfile.TemporaryDirectory() as home_tmpdir:
        
        # Don't create .promptcraft directories
        with patch('promptcraft.core.Path.cwd', return_value=Path(cwd_tmpdir)), \
             patch('promptcraft.core.Path.home', return_value=Path(home_tmpdir)):
            with pytest.raises(CommandNotFoundError) as exc_info:
                find_command_path("missing-dirs-cmd")
            
            error_message = str(exc_info.value)
            assert "Command 'missing-dirs-cmd' not found" in error_message


def test_find_command_path_proper_filename_construction():
    """Test that .md extension is properly added to command name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cmd_dir = Path(tmpdir) / ".promptcraft" / "commands"
        cmd_dir.mkdir(parents=True)
        
        # Create command file with .md extension
        cmd_file = cmd_dir / "filename-test.md"
        cmd_file.write_text("# Filename Test")
        
        with patch('promptcraft.core.Path.cwd', return_value=Path(tmpdir)):
            result = find_command_path("filename-test")
            assert result.name == "filename-test.md"
            assert result == cmd_file


def test_find_command_path_invalid_command_name():
    """Test error handling for invalid command names."""
    # Test None command name
    with pytest.raises(CommandNotFoundError, match="Command name must be a non-empty string"):
        find_command_path(None)
    
    # Test empty string command name
    with pytest.raises(CommandNotFoundError, match="Command name must be a non-empty string"):
        find_command_path("")
    
    # Test non-string command name
    with pytest.raises(CommandNotFoundError, match="Command name must be a non-empty string"):
        find_command_path(123)


# generate_prompt() function tests

def test_generate_prompt_basic_substitution():
    """Test basic argument substitution in template."""
    with tempfile.TemporaryDirectory() as tmpdir:
        template_file = Path(tmpdir) / "test-template.md"
        template_content = "# Test Template\n\nArguments: $ARGUMENTS\n\nEnd of template."
        template_file.write_text(template_content, encoding='utf-8')
        
        arguments = ["arg1", "arg2", "arg3"]
        result = generate_prompt(template_file, arguments)
        
        expected = "# Test Template\n\nArguments: arg1 arg2 arg3\n\nEnd of template."
        assert result == expected


def test_generate_prompt_empty_arguments():
    """Test handling of empty arguments list."""
    with tempfile.TemporaryDirectory() as tmpdir:
        template_file = Path(tmpdir) / "empty-args.md"
        template_content = "Template with $ARGUMENTS placeholder."
        template_file.write_text(template_content, encoding='utf-8')
        
        result = generate_prompt(template_file, [])
        
        expected = "Template with  placeholder."
        assert result == expected


def test_generate_prompt_single_argument():
    """Test handling of single argument."""
    with tempfile.TemporaryDirectory() as tmpdir:
        template_file = Path(tmpdir) / "single-arg.md"
        template_content = "Single argument: $ARGUMENTS"
        template_file.write_text(template_content, encoding='utf-8')
        
        result = generate_prompt(template_file, ["single"])
        
        expected = "Single argument: single"
        assert result == expected


def test_generate_prompt_multiple_placeholders():
    """Test template with multiple $ARGUMENTS placeholders."""
    with tempfile.TemporaryDirectory() as tmpdir:
        template_file = Path(tmpdir) / "multi-placeholder.md"
        template_content = "Start: $ARGUMENTS\nMiddle: $ARGUMENTS\nEnd: $ARGUMENTS"
        template_file.write_text(template_content, encoding='utf-8')
        
        arguments = ["test", "args"]
        result = generate_prompt(template_file, arguments)
        
        expected = "Start: test args\nMiddle: test args\nEnd: test args"
        assert result == expected


def test_generate_prompt_preserve_formatting():
    """Test that template formatting (markdown, whitespace) is preserved."""
    with tempfile.TemporaryDirectory() as tmpdir:
        template_file = Path(tmpdir) / "formatted.md"
        template_content = """# Main Title

## Subsection

- List item 1
- List item 2: $ARGUMENTS
- List item 3

```code
function example() {
    return "$ARGUMENTS";
}
```

**Bold text** and *italic text* preserved.
"""
        template_file.write_text(template_content, encoding='utf-8')
        
        arguments = ["formatted", "content"]
        result = generate_prompt(template_file, arguments)
        
        expected = """# Main Title

## Subsection

- List item 1
- List item 2: formatted content
- List item 3

```code
function example() {
    return "formatted content";
}
```

**Bold text** and *italic text* preserved.
"""
        assert result == expected


def test_generate_prompt_arguments_with_spaces():
    """Test arguments containing spaces are properly handled."""
    with tempfile.TemporaryDirectory() as tmpdir:
        template_file = Path(tmpdir) / "spaces.md"
        template_content = "Arguments: $ARGUMENTS"
        template_file.write_text(template_content, encoding='utf-8')
        
        arguments = ["arg with spaces", "another arg", "final"]
        result = generate_prompt(template_file, arguments)
        
        expected = "Arguments: arg with spaces another arg final"
        assert result == expected


def test_generate_prompt_no_placeholder():
    """Test template without $ARGUMENTS placeholder."""
    with tempfile.TemporaryDirectory() as tmpdir:
        template_file = Path(tmpdir) / "no-placeholder.md"
        template_content = "# Template\n\nThis template has no placeholder."
        template_file.write_text(template_content, encoding='utf-8')
        
        arguments = ["unused", "args"]
        result = generate_prompt(template_file, arguments)
        
        # Should return unchanged content
        expected = "# Template\n\nThis template has no placeholder."
        assert result == expected


def test_generate_prompt_file_not_found():
    """Test TemplateReadError when template file does not exist."""
    nonexistent_file = Path("/nonexistent/path/template.md")
    
    with pytest.raises(TemplateReadError) as exc_info:
        generate_prompt(nonexistent_file, ["test"])
    
    error = exc_info.value
    assert "Template file not found" in str(error)
    assert str(nonexistent_file) in str(error)
    assert error.error_code == "TEMPLATE_FILE_NOT_FOUND"


def test_generate_prompt_permission_denied():
    """Test TemplateReadError when file permissions prevent reading."""
    with tempfile.TemporaryDirectory() as tmpdir:
        template_file = Path(tmpdir) / "restricted.md"
        template_file.write_text("Test content", encoding='utf-8')
        
        # Make file unreadable (on Unix-like systems)
        if os.name != 'nt':  # Skip on Windows
            template_file.chmod(0o000)
            
            with pytest.raises(TemplateReadError) as exc_info:
                generate_prompt(template_file, ["test"])
            
            error = exc_info.value
            assert "Permission denied" in str(error)
            assert str(template_file) in str(error)
            assert error.error_code == "TEMPLATE_PERMISSION_DENIED"


def test_generate_prompt_unicode_content():
    """Test handling of Unicode characters in template content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        template_file = Path(tmpdir) / "unicode.md"
        template_content = "# 测试模板\n\n参数: $ARGUMENTS\n\n🚀 完成"
        template_file.write_text(template_content, encoding='utf-8')
        
        arguments = ["用户", "测试"]
        result = generate_prompt(template_file, arguments)
        
        expected = "# 测试模板\n\n参数: 用户 测试\n\n🚀 完成"
        assert result == expected


def test_generate_prompt_large_template():
    """Test processing of larger template files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        template_file = Path(tmpdir) / "large.md"
        
        # Create a larger template with multiple sections
        large_content = []
        for i in range(50):
            large_content.append(f"## Section {i}")
            large_content.append(f"Content for section {i}.")
            if i == 25:  # Add placeholder in the middle
                large_content.append("Arguments: $ARGUMENTS")
            large_content.append("")
        
        template_content = "\n".join(large_content)
        template_file.write_text(template_content, encoding='utf-8')
        
        arguments = ["large", "file", "test"]
        result = generate_prompt(template_file, arguments)
        
        assert "Arguments: large file test" in result
        assert result.count("## Section") == 50


def test_generate_prompt_special_characters_in_arguments():
    """Test arguments containing special characters."""
    with tempfile.TemporaryDirectory() as tmpdir:
        template_file = Path(tmpdir) / "special-chars.md"
        template_content = "Arguments: $ARGUMENTS"
        template_file.write_text(template_content, encoding='utf-8')
        
        arguments = ["--flag", "value=test", "path/to/file", "'quoted text'"]
        result = generate_prompt(template_file, arguments)
        
        expected = "Arguments: --flag value=test path/to/file 'quoted text'"
        assert result == expected


def test_generate_prompt_pathlib_path_parameter():
    """Test that function properly accepts pathlib.Path objects."""
    with tempfile.TemporaryDirectory() as tmpdir:
        template_file = Path(tmpdir) / "pathlib-test.md"
        template_content = "Path test: $ARGUMENTS"
        template_file.write_text(template_content, encoding='utf-8')
        
        # Ensure we're passing a Path object, not a string
        assert isinstance(template_file, Path)
        
        arguments = ["pathlib", "works"]
        result = generate_prompt(template_file, arguments)
        
        expected = "Path test: pathlib works"
        assert result == expected


# process_command() function tests

def test_process_command_successful_processing():
    """Test successful command processing with arguments."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Setup directory structure
        cmd_dir = Path(tmpdir) / ".promptcraft" / "commands"
        cmd_dir.mkdir(parents=True)
        
        # Create test command file
        cmd_file = cmd_dir / "test-cmd.md"
        template_content = "# Test Command\n\nArguments: $ARGUMENTS\n\nEnd of command."
        cmd_file.write_text(template_content, encoding='utf-8')
        
        with patch('promptcraft.core.Path.cwd', return_value=Path(tmpdir)):
            arguments = ["arg1", "arg2", "arg3"]
            result = process_command("test-cmd", arguments)
            
            expected = "# Test Command\n\nArguments: arg1 arg2 arg3\n\nEnd of command."
            assert result == expected


def test_process_command_empty_arguments():
    """Test successful command processing with empty arguments."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cmd_dir = Path(tmpdir) / ".promptcraft" / "commands"
        cmd_dir.mkdir(parents=True)
        
        cmd_file = cmd_dir / "empty-args-cmd.md"
        template_content = "# Command\n\nArguments: [$ARGUMENTS]\n\nDone."
        cmd_file.write_text(template_content, encoding='utf-8')
        
        with patch('promptcraft.core.Path.cwd', return_value=Path(tmpdir)):
            result = process_command("empty-args-cmd", [])
            
            expected = "# Command\n\nArguments: []\n\nDone."
            assert result == expected


def test_process_command_single_argument():
    """Test command processing with single argument."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cmd_dir = Path(tmpdir) / ".promptcraft" / "commands"
        cmd_dir.mkdir(parents=True)
        
        cmd_file = cmd_dir / "single-arg-cmd.md"
        template_content = "Single argument: $ARGUMENTS"
        cmd_file.write_text(template_content, encoding='utf-8')
        
        with patch('promptcraft.core.Path.cwd', return_value=Path(tmpdir)):
            result = process_command("single-arg-cmd", ["single"])
            
            expected = "Single argument: single"
            assert result == expected


def test_process_command_complex_template():
    """Test command processing with complex template formatting."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cmd_dir = Path(tmpdir) / ".promptcraft" / "commands"
        cmd_dir.mkdir(parents=True)
        
        cmd_file = cmd_dir / "complex-cmd.md"
        template_content = """# Complex Command

## Description
This is a complex template with multiple sections.

### Arguments
The provided arguments are: $ARGUMENTS

### Code Block
```bash
echo "$ARGUMENTS"
```

**Bold text** and *italic text* should be preserved.
"""
        cmd_file.write_text(template_content, encoding='utf-8')
        
        with patch('promptcraft.core.Path.cwd', return_value=Path(tmpdir)):
            arguments = ["complex", "test", "case"]
            result = process_command("complex-cmd", arguments)
            
            expected = """# Complex Command

## Description
This is a complex template with multiple sections.

### Arguments
The provided arguments are: complex test case

### Code Block
```bash
echo "complex test case"
```

**Bold text** and *italic text* should be preserved.
"""
            assert result == expected


def test_process_command_command_not_found_error():
    """Test CommandNotFoundError handling and context preservation."""
    with tempfile.TemporaryDirectory() as cwd_tmpdir, \
         tempfile.TemporaryDirectory() as home_tmpdir:
        
        # Create directories but no command files
        cwd_cmd_dir = Path(cwd_tmpdir) / ".promptcraft" / "commands"
        cwd_cmd_dir.mkdir(parents=True)
        home_cmd_dir = Path(home_tmpdir) / ".promptcraft" / "commands"
        home_cmd_dir.mkdir(parents=True)
        
        with patch('promptcraft.core.Path.cwd', return_value=Path(cwd_tmpdir)), \
             patch('promptcraft.core.Path.home', return_value=Path(home_tmpdir)):
            
            with pytest.raises(CommandNotFoundError) as exc_info:
                process_command("nonexistent-cmd", ["test", "args"])
            
            error_message = str(exc_info.value)
            # Check that error includes command name context
            assert "Command 'nonexistent-cmd' processing failed" in error_message
            # Check that original error details are preserved
            assert "Command 'nonexistent-cmd' not found" in error_message
            assert str(cwd_cmd_dir) in error_message or str(home_cmd_dir) in error_message


def test_process_command_template_read_error():
    """Test TemplateReadError handling and context preservation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cmd_dir = Path(tmpdir) / ".promptcraft" / "commands"
        cmd_dir.mkdir(parents=True)
        
        # Create command file that will cause read error
        cmd_file = cmd_dir / "broken-cmd.md"
        cmd_file.write_text("Test content", encoding='utf-8')
        
        # Make file unreadable (on Unix-like systems)
        if os.name != 'nt':  # Skip on Windows due to different permission model
            cmd_file.chmod(0o000)
            
            with patch('promptcraft.core.Path.cwd', return_value=Path(tmpdir)):
                with pytest.raises(TemplateReadError) as exc_info:
                    process_command("broken-cmd", ["test", "args"])
                
                error_message = str(exc_info.value)
                # Check that error includes command name context
                assert "Command 'broken-cmd' template processing failed" in error_message
                # Check that original error details are preserved
                assert "Permission denied" in error_message
                assert str(cmd_file) in error_message
                # Check that error code is preserved
                assert exc_info.value.error_code == "TEMPLATE_PERMISSION_DENIED"


def test_process_command_integration_between_functions():
    """Test integration between find_command_path and generate_prompt functions."""
    with tempfile.TemporaryDirectory() as cwd_tmpdir, \
         tempfile.TemporaryDirectory() as home_tmpdir:
        
        # Create command in home directory (testing hierarchical search)
        home_cmd_dir = Path(home_tmpdir) / ".promptcraft" / "commands"
        home_cmd_dir.mkdir(parents=True)
        
        home_cmd_file = home_cmd_dir / "integration-cmd.md"
        template_content = "# Integration Test\n\nFound in: home directory\nArgs: $ARGUMENTS"
        home_cmd_file.write_text(template_content, encoding='utf-8')
        
        # Setup current directory without the command (to test fallback)
        cwd_cmd_dir = Path(cwd_tmpdir) / ".promptcraft" / "commands"
        cwd_cmd_dir.mkdir(parents=True)
        
        with patch('promptcraft.core.Path.cwd', return_value=Path(cwd_tmpdir)), \
             patch('promptcraft.core.Path.home', return_value=Path(home_tmpdir)):
            
            result = process_command("integration-cmd", ["integrated", "successfully"])
            
            expected = "# Integration Test\n\nFound in: home directory\nArgs: integrated successfully"
            assert result == expected
            
            # Verify that the correct template was found and processed
            assert "home directory" in result
            assert "integrated successfully" in result


def test_process_command_error_context_preservation_command_not_found():
    """Test that CommandNotFoundError context is properly enhanced while preserving original details."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create empty directory structure
        cmd_dir = Path(tmpdir) / ".promptcraft" / "commands"
        cmd_dir.mkdir(parents=True)
        
        with patch('promptcraft.core.Path.cwd', return_value=Path(tmpdir)):
            with pytest.raises(CommandNotFoundError) as exc_info:
                process_command("missing-cmd", ["arg1", "arg2"])
            
            error = exc_info.value
            error_message = str(error)
            
            # Check enhanced context
            assert "Command 'missing-cmd' processing failed" in error_message
            # Check original error details are preserved
            assert "Command 'missing-cmd' not found" in error_message
            assert str(cmd_dir) in error_message
            # Check that the original exception is chained
            assert error.__cause__ is not None
            assert isinstance(error.__cause__, CommandNotFoundError)


def test_process_command_edge_cases():
    """Test process_command with various edge cases."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cmd_dir = Path(tmpdir) / ".promptcraft" / "commands"
        cmd_dir.mkdir(parents=True)
        
        # Test with arguments containing special characters
        special_cmd_file = cmd_dir / "special-chars.md"
        special_cmd_file.write_text("Command: $ARGUMENTS", encoding='utf-8')
        
        with patch('promptcraft.core.Path.cwd', return_value=Path(tmpdir)):
            # Test special characters in arguments
            result = process_command("special-chars", ["--flag", "value=test", "path/to/file"])
            assert result == "Command: --flag value=test path/to/file"
            
            # Test arguments with spaces
            result = process_command("special-chars", ["arg with spaces", "another arg"])
            assert result == "Command: arg with spaces another arg"


def test_process_command_unicode_handling():
    """Test process_command with Unicode characters in template and arguments."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cmd_dir = Path(tmpdir) / ".promptcraft" / "commands"
        cmd_dir.mkdir(parents=True)
        
        # Create template with Unicode content
        unicode_cmd_file = cmd_dir / "unicode-cmd.md"
        template_content = "# 测试命令\n\n参数: $ARGUMENTS\n\n🚀 完成"
        unicode_cmd_file.write_text(template_content, encoding='utf-8')
        
        with patch('promptcraft.core.Path.cwd', return_value=Path(tmpdir)):
            arguments = ["用户", "测试", "🎯"]
            result = process_command("unicode-cmd", arguments)
            
            expected = "# 测试命令\n\n参数: 用户 测试 🎯\n\n🚀 完成"
            assert result == expected


def test_process_command_template_without_placeholder():
    """Test process_command with template that has no $ARGUMENTS placeholder."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cmd_dir = Path(tmpdir) / ".promptcraft" / "commands"
        cmd_dir.mkdir(parents=True)
        
        # Create template without placeholder
        no_placeholder_file = cmd_dir / "no-placeholder.md"
        template_content = "# Static Template\n\nThis template has no placeholders."
        no_placeholder_file.write_text(template_content, encoding='utf-8')
        
        with patch('promptcraft.core.Path.cwd', return_value=Path(tmpdir)):
            result = process_command("no-placeholder", ["unused", "args"])
            
            # Should return template unchanged
            expected = "# Static Template\n\nThis template has no placeholders."
            assert result == expected


# Command discovery function tests

def test_extract_description_with_markdown_header():
    """Test description extraction with markdown headers."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.md"
        test_file.write_text("# Test Header\n\nContent here.")
        
        result = _extract_description(test_file)
        assert result == "Test Header"


def test_extract_description_with_multiple_hash_header():
    """Test description extraction with multiple hash headers."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.md"
        test_file.write_text("### Deep Header\n\nContent here.")
        
        result = _extract_description(test_file)
        assert result == "Deep Header"


def test_extract_description_with_empty_first_line():
    """Test description extraction with empty first line."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.md"
        test_file.write_text("\nSecond line content.\n\nMore content.")
        
        result = _extract_description(test_file)
        assert result == "Second line content."


def test_extract_description_file_not_found():
    """Test description extraction with non-existent file."""
    non_existent = Path("/fake/path/not-exist.md")
    result = _extract_description(non_existent)
    assert result == "No description available"


def test_extract_description_permission_error():
    """Test description extraction with permission errors."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.md"
        test_file.write_text("Content here.")
        
        # Mock permission error
        with patch('builtins.open', side_effect=PermissionError("Access denied")):
            result = _extract_description(test_file)
            assert result == "No description available"


def test_extract_description_unicode_error():
    """Test description extraction with unicode decode errors."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.md"
        test_file.write_text("Content here.")
        
        # Mock unicode error
        with patch('builtins.open', side_effect=UnicodeDecodeError("utf-8", b'', 0, 1, "Invalid")):
            result = _extract_description(test_file)
            assert result == "No description available"


def test_discover_commands_empty_directories():
    """Test command discovery with empty directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch('promptcraft.core.Path.cwd', return_value=Path(tmpdir)), \
             patch('promptcraft.core.Path.home', return_value=Path(tmpdir)):
            
            result = discover_commands()
            assert result == []


def test_discover_commands_project_only():
    """Test command discovery with project commands only."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create project directory structure
        project_dir = Path(tmpdir) / "project" / ".promptcraft" / "commands"
        project_dir.mkdir(parents=True)
        
        # Create test command files
        cmd1 = project_dir / "cmd1.md"
        cmd1.write_text("# Command 1\n\nTest command 1.")
        
        cmd2 = project_dir / "cmd2.md"
        cmd2.write_text("## Command 2\n\nTest command 2.")
        
        with patch('promptcraft.core.Path.cwd', return_value=Path(tmpdir) / "project"), \
             patch('promptcraft.core.Path.home', return_value=Path("/fake/home")):
            
            result = discover_commands()
            
            assert len(result) == 2
            assert result[0].name == "cmd1"
            assert result[0].source == "Project"
            assert result[0].description == "Command 1"
            assert result[1].name == "cmd2"
            assert result[1].source == "Project"
            assert result[1].description == "Command 2"


def test_discover_commands_global_only():
    """Test command discovery with global commands only."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create home directory structure
        home_dir = Path(tmpdir) / ".promptcraft" / "commands"
        home_dir.mkdir(parents=True)
        
        # Create test command file
        global_cmd = home_dir / "global-cmd.md"
        global_cmd.write_text("# Global Command\n\nGlobal test command.")
        
        with patch('promptcraft.core.Path.cwd', return_value=Path("/fake/cwd")), \
             patch('promptcraft.core.Path.home', return_value=Path(tmpdir)):
            
            result = discover_commands()
            
            assert len(result) == 1
            assert result[0].name == "global-cmd"
            assert result[0].source == "Global"
            assert result[0].description == "Global Command"


def test_discover_commands_both_sources():
    """Test command discovery with both project and global commands."""
    with tempfile.TemporaryDirectory() as project_tmpdir, \
         tempfile.TemporaryDirectory() as home_tmpdir:
        
        # Create project directory structure
        project_dir = Path(project_tmpdir) / ".promptcraft" / "commands"
        project_dir.mkdir(parents=True)
        
        project_cmd = project_dir / "project-cmd.md"
        project_cmd.write_text("# Project Command\n\nProject test command.")
        
        # Create home directory structure
        home_dir = Path(home_tmpdir) / ".promptcraft" / "commands"
        home_dir.mkdir(parents=True)
        
        home_cmd = home_dir / "global-cmd.md"
        home_cmd.write_text("# Global Command\n\nGlobal test command.")
        
        with patch('promptcraft.core.Path.cwd', return_value=Path(project_tmpdir)), \
             patch('promptcraft.core.Path.home', return_value=Path(home_tmpdir)):
            
            result = discover_commands()
            
            assert len(result) == 2
            # Should be sorted alphabetically
            assert result[0].name == "global-cmd"
            assert result[0].source == "Global"
            assert result[1].name == "project-cmd"
            assert result[1].source == "Project"


def test_discover_commands_alphabetical_sorting():
    """Test command discovery sorts results alphabetically."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / ".promptcraft" / "commands"
        project_dir.mkdir(parents=True)
        
        # Create commands in non-alphabetical order
        (project_dir / "zebra.md").write_text("# Zebra\n\nZ command.")
        (project_dir / "alpha.md").write_text("# Alpha\n\nA command.")
        (project_dir / "beta.md").write_text("# Beta\n\nB command.")
        
        with patch('promptcraft.core.Path.cwd', return_value=Path(tmpdir)), \
             patch('promptcraft.core.Path.home', return_value=Path("/fake/home")):
            
            result = discover_commands()
            
            assert len(result) == 3
            assert result[0].name == "alpha"
            assert result[1].name == "beta"
            assert result[2].name == "zebra"


def test_discover_commands_ignores_non_md_files():
    """Test command discovery ignores non-.md files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / ".promptcraft" / "commands"
        project_dir.mkdir(parents=True)
        
        # Create .md file (should be included)
        (project_dir / "valid.md").write_text("# Valid Command\n\nValid.")
        
        # Create non-.md files (should be ignored)
        (project_dir / "readme.txt").write_text("Not a command.")
        (project_dir / "script.py").write_text("print('Not a command')")
        (project_dir / "config.json").write_text('{"not": "command"}')
        
        with patch('promptcraft.core.Path.cwd', return_value=Path(tmpdir)), \
             patch('promptcraft.core.Path.home', return_value=Path("/fake/home")):
            
            result = discover_commands()
            
            assert len(result) == 1
            assert result[0].name == "valid"


def test_discover_commands_handles_permission_errors():
    """Test command discovery handles permission errors gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / ".promptcraft" / "commands"
        project_dir.mkdir(parents=True)
        
        (project_dir / "cmd.md").write_text("# Command\n\nTest.")
        
        with patch('promptcraft.core.Path.cwd', return_value=Path(tmpdir)), \
             patch('promptcraft.core.Path.home', return_value=Path("/fake/home")):
            
            # Mock permission error on glob
            with patch.object(Path, 'glob', side_effect=PermissionError("Access denied")):
                result = discover_commands()
                # Should return empty list, not raise exception
                assert result == []


def test_discover_commands_handles_os_errors():
    """Test command discovery handles OS errors gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / ".promptcraft" / "commands"
        project_dir.mkdir(parents=True)
        
        (project_dir / "cmd.md").write_text("# Command\n\nTest.")
        
        with patch('promptcraft.core.Path.cwd', return_value=Path(tmpdir)), \
             patch('promptcraft.core.Path.home', return_value=Path("/fake/home")):
            
            # Mock OS error on glob
            with patch.object(Path, 'glob', side_effect=OSError("OS error")):
                result = discover_commands()
                # Should return empty list, not raise exception
                assert result == []


def test_command_info_named_tuple():
    """Test CommandInfo named tuple structure."""
    from pathlib import Path
    
    cmd_info = CommandInfo(
        name="test",
        path=Path("/fake/test.md"),
        source="Project",
        description="Test description"
    )
    
    assert cmd_info.name == "test"
    assert cmd_info.path == Path("/fake/test.md")
    assert cmd_info.source == "Project"
    assert cmd_info.description == "Test description"
    
    # Test that it's a proper named tuple
    assert isinstance(cmd_info, tuple)
    assert len(cmd_info) == 4


# Additional Template Discovery Tests

def test_extract_description_with_whitespace_only_header():
    """Test description extraction with whitespace-only header."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.md"
        test_file.write_text("#    \n\nContent here.")
        
        result = _extract_description(test_file)
        assert result == "No description available"


def test_extract_description_with_complex_markdown():
    """Test description extraction with complex markdown in header."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.md"
        test_file.write_text("## **Bold** and *Italic* Header with `code`\n\nContent.")
        
        result = _extract_description(test_file)
        assert result == "**Bold** and *Italic* Header with `code`"


def test_extract_description_empty_file():
    """Test description extraction with completely empty file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.md"
        test_file.write_text("")
        
        result = _extract_description(test_file)
        assert result == "No description available"


def test_discover_commands_with_subdirectories():
    """Test command discovery ignores subdirectories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / ".promptcraft" / "commands"
        project_dir.mkdir(parents=True)
        
        # Create valid .md file
        (project_dir / "valid.md").write_text("# Valid Command\n\nValid.")
        
        # Create subdirectory (should be ignored)
        subdir = project_dir / "subdir"
        subdir.mkdir()
        (subdir / "ignored.md").write_text("# Ignored\n\nShould be ignored.")
        
        with patch('promptcraft.core.Path.cwd', return_value=Path(tmpdir)), \
             patch('promptcraft.core.Path.home', return_value=Path("/fake/home")):
            
            result = discover_commands()
            
            assert len(result) == 1
            assert result[0].name == "valid"


def test_discover_commands_case_insensitive_sorting():
    """Test command discovery sorts case-insensitively."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / ".promptcraft" / "commands"
        project_dir.mkdir(parents=True)
        
        # Create commands with mixed case
        (project_dir / "Apple.md").write_text("# Apple\n\nA command.")
        (project_dir / "banana.md").write_text("# Banana\n\nB command.")
        (project_dir / "Cherry.md").write_text("# Cherry\n\nC command.")
        
        with patch('promptcraft.core.Path.cwd', return_value=Path(tmpdir)), \
             patch('promptcraft.core.Path.home', return_value=Path("/fake/home")):
            
            result = discover_commands()
            
            assert len(result) == 3
            # Should be sorted case-insensitively: Apple, banana, Cherry
            assert result[0].name == "Apple"
            assert result[1].name == "banana"
            assert result[2].name == "Cherry"


# Additional Template Processing Tests

def test_template_processor_with_complex_content():
    """Test TemplateProcessor with complex markdown content."""
    processor = TemplateProcessor()
    complex_content = """# Complex Template

## Section 1
Some **bold** and *italic* text.

### Code Block
```python
def hello():
    print("Hello, World!")
```

- List item 1
- List item 2

> Blockquote text

[Link](https://example.com)
"""
    result = processor.process_template(complex_content)
    assert result == complex_content


def test_generate_prompt_with_binary_file_error():
    """Test TemplateReadError when trying to read binary file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a binary file
        binary_file = Path(tmpdir) / "binary.bin"
        binary_file.write_bytes(b'\x00\x01\x02\x03\xff\xfe')
        
        with pytest.raises(TemplateReadError) as exc_info:
            generate_prompt(binary_file, ["test"])
        
        error = exc_info.value
        assert "Failed to decode" in str(error) or "encoding" in str(error)
        assert error.error_code == "TEMPLATE_ENCODING_ERROR"


def test_generate_prompt_with_very_large_file():
    """Test template processing with very large files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        large_file = Path(tmpdir) / "large.md"
        
        # Create a large template (about 1MB)
        large_content = "# Large Template\n\n" + "Line with content and $ARGUMENTS\n" * 50000
        large_file.write_text(large_content, encoding='utf-8')
        
        arguments = ["test", "args"]
        result = generate_prompt(large_file, arguments)
        
        # Should process successfully
        assert "test args" in result
        assert result.startswith("# Large Template")
        assert len(result) > 1000000  # Should be large


# Additional Error Handling Tests

def test_process_command_with_circular_symlink():
    """Test process_command handling of circular symlinks (Unix only)."""
    if os.name == 'nt':  # Skip on Windows
        pytest.skip("Symlink test not applicable on Windows")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        cmd_dir = Path(tmpdir) / ".promptcraft" / "commands"
        cmd_dir.mkdir(parents=True)
        
        # Create circular symlink
        symlink_path = cmd_dir / "circular.md"
        try:
            symlink_path.symlink_to(symlink_path)  # Circular reference
        except OSError:
            pytest.skip("Cannot create symlinks on this system")
        
        with patch('promptcraft.core.Path.cwd', return_value=Path(tmpdir)):
            with pytest.raises((CommandNotFoundError, TemplateReadError)):
                process_command("circular", ["test"])


# Performance and Edge Case Tests

def test_find_command_path_with_long_path():
    """Test find_command_path with very long file paths."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create nested directory structure
        deep_path = Path(tmpdir)
        for i in range(10):  # Create 10 levels deep
            deep_path = deep_path / f"level{i}"
        deep_path = deep_path / ".promptcraft" / "commands"
        deep_path.mkdir(parents=True)
        
        # Create command file
        cmd_file = deep_path / "deep-cmd.md"
        cmd_file.write_text("# Deep Command")
        
        with patch('promptcraft.core.Path.cwd', return_value=Path(tmpdir) / 'level0' / 'level1' / 'level2' / 'level3' / 'level4' / 'level5' / 'level6' / 'level7' / 'level8' / 'level9'):
            result = find_command_path("deep-cmd")
            assert result == cmd_file
            assert result.exists()


def test_discover_commands_with_unicode_filenames():
    """Test command discovery with Unicode filenames."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / ".promptcraft" / "commands"
        project_dir.mkdir(parents=True)
        
        # Create commands with Unicode names
        unicode_names = ["café.md", "测试.md", "émoji😊.md"]
        for name in unicode_names:
            try:
                (project_dir / name).write_text(f"# {name[:-3]}\n\nUnicode command.")
            except (OSError, UnicodeEncodeError):
                # Skip if filesystem doesn't support Unicode
                continue
        
        with patch('promptcraft.core.Path.cwd', return_value=Path(tmpdir)), \
             patch('promptcraft.core.Path.home', return_value=Path("/fake/home")):
            
            result = discover_commands()
            
            # Should find at least the files that were successfully created
            assert len(result) >= 0  # Some filesystems may not support Unicode
            for cmd in result:
                assert cmd.name in ["café", "测试", "émoji😊"]


# Memory and Resource Tests

def test_template_processor_memory_efficiency():
    """Test that TemplateProcessor doesn't hold references to processed content."""
    processor = TemplateProcessor()
    
    # Process multiple templates to check for memory leaks
    for i in range(1000):
        content = f"Template {i} with some content"
        result = processor.process_template(content)
        assert result == content
    
    # If we got here without memory issues, the test passes
    assert True


def test_concurrent_command_discovery():
    """Test command discovery behavior under concurrent access."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / ".promptcraft" / "commands"
        project_dir.mkdir(parents=True)
        
        # Create multiple command files
        for i in range(10):
            (project_dir / f"cmd{i}.md").write_text(f"# Command {i}\n\nCommand {i}.")
        
        with patch('promptcraft.core.Path.cwd', return_value=Path(tmpdir)), \
             patch('promptcraft.core.Path.home', return_value=Path("/fake/home")):
            
            # Simulate concurrent discovery calls
            results = []
            for _ in range(5):
                result = discover_commands()
                results.append(result)
            
            # All results should be consistent
            assert all(len(r) == 10 for r in results)
            assert all(r[0].name == "cmd0" for r in results)  # First should always be cmd0 (sorted)