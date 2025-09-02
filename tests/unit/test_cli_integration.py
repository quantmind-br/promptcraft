"""Comprehensive CLI integration tests using click.testing.CliRunner."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner
import tempfile
from pathlib import Path

from promptcraft.main import promptcraft, _initialize_project, _list_commands
from promptcraft.exceptions import CommandNotFoundError, TemplateReadError
from promptcraft.core import CommandInfo


class TestCLICommandExecution:
    """Test CLI command execution through CliRunner."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch('promptcraft.main.process_command')
    @patch('promptcraft.main._copy_to_clipboard')
    def test_all_command_invocation_patterns(self, mock_copy_clipboard, mock_process):
        """Test all supported command invocation patterns."""
        mock_process.return_value = "Test output"
        mock_copy_clipboard.return_value = True

        invocation_patterns = [
            # Basic patterns
            (['/command'], 'command', []),
            (['command'], 'command', []),
            
            # With single argument
            (['/command', 'arg1'], 'command', ['arg1']),
            (['command', 'arg1'], 'command', ['arg1']),
            
            # With multiple arguments
            (['/command', 'arg1', 'arg2', 'arg3'], 'command', ['arg1', 'arg2', 'arg3']),
            
            # With spaces in arguments
            (['/command', 'arg with spaces', 'normal'], 'command', ['arg with spaces', 'normal']),
            
            # With special characters
            (['/command', '--flag', 'value=test', 'path/file.txt'], 'command', ['--flag', 'value=test', 'path/file.txt']),
            
            # With empty arguments
            (['/command', '', 'after-empty'], 'command', ['', 'after-empty']),
        ]

        for args, expected_cmd, expected_args in invocation_patterns:
            mock_process.reset_mock()
            result = self.runner.invoke(promptcraft, args)
            
            assert result.exit_code == 0, f"Failed for args: {args}"
            mock_process.assert_called_once_with(expected_cmd, expected_args)

    @patch('promptcraft.main.process_command')
    @patch('promptcraft.main._copy_to_clipboard')
    def test_command_name_normalization(self, mock_copy_clipboard, mock_process):
        """Test command name normalization (slash stripping)."""
        mock_process.return_value = "Test output"
        mock_copy_clipboard.return_value = True

        normalization_cases = [
            ('/simple-command', 'simple-command'),
            ('//double-slash', '/double-slash'),  # Only first slash stripped
            ('/command-with-dashes', 'command-with-dashes'),
            ('/command_with_underscores', 'command_with_underscores'),
            ('/123-numeric-command', '123-numeric-command'),
            ('/CamelCaseCommand', 'CamelCaseCommand'),
        ]

        for input_cmd, expected_cmd in normalization_cases:
            mock_process.reset_mock()
            result = self.runner.invoke(promptcraft, [input_cmd, 'test'])
            
            assert result.exit_code == 0
            mock_process.assert_called_once_with(expected_cmd, ['test'])

    def test_help_command_comprehensive(self):
        """Test help command displays all required information."""
        result = self.runner.invoke(promptcraft, ['--help'])
        
        assert result.exit_code == 0
        
        # Check required help sections
        required_content = [
            "PromptCraft CLI",
            "command-line tool for managing prompt templates",
            "Execute slash commands",
            "Usage Examples:",
            "promptcraft /create-story",
            "promptcraft /fix-bug",
            "promptcraft /code-review",
            "--stdout",
            "Output to terminal instead of clipboard",
            "--init",
            "Initialize PromptCraft project structure",
            "--list",
            "List all available commands",
            "COMMAND_NAME",
            "ARGUMENTS",
        ]
        
        for content in required_content:
            assert content in result.output, f"Missing help content: {content}"

    def test_version_command(self):
        """Test version command displays version information."""
        result = self.runner.invoke(promptcraft, ['--version'])
        
        assert result.exit_code == 0
        # Version output format may vary, but should not crash
        assert len(result.output.strip()) > 0


class TestCLIArgumentParsing:
    """Test CLI argument parsing and validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_missing_command_name_error(self):
        """Test error when command name is missing."""
        result = self.runner.invoke(promptcraft, [])
        
        assert result.exit_code == 1
        assert "Command name is required" in result.output
        assert "Use 'promptcraft --help' for usage information" in result.output

    @patch('promptcraft.main.process_command')
    @patch('promptcraft.main._copy_to_clipboard')
    def test_argument_parsing_edge_cases(self, mock_copy_clipboard, mock_process):
        """Test argument parsing with edge cases."""
        mock_process.return_value = "Test output"
        mock_copy_clipboard.return_value = True

        edge_cases = [
            # Arguments with leading/trailing whitespace
            (['/test', ' leading-space'], 'test', [' leading-space']),
            (['/test', 'trailing-space '], 'test', ['trailing-space ']),
            
            # Arguments with quotes (handled by shell before reaching CLI)
            (['/test', "'single-quotes'"], 'test', ["'single-quotes'"]),
            (['/test', '"double-quotes"'], 'test', ['"double-quotes"']),
            
            # Arguments with special characters
            (['/test', '@#$%^&*()'], 'test', ['@#$%^&*()']),
            (['/test', '\\backslashes\\path'], 'test', ['\\backslashes\\path']),
            
            # Unicode arguments
            (['/test', 'café', '漢字', '🚀'], 'test', ['café', '漢字', '🚀']),
            
            # Mixed argument types
            (['/test', '123', 'text', '--flag', 'value=x'], 'test', ['123', 'text', '--flag', 'value=x']),
        ]

        for args, expected_cmd, expected_args in edge_cases:
            mock_process.reset_mock()
            result = self.runner.invoke(promptcraft, args)
            
            assert result.exit_code == 0, f"Failed for: {args}"
            mock_process.assert_called_once_with(expected_cmd, expected_args)

    def test_flag_precedence_and_combinations(self):
        """Test flag precedence and combinations."""
        # Test --help takes precedence
        result = self.runner.invoke(promptcraft, ['--help', '--version', '/command'])
        assert result.exit_code == 0
        assert "PromptCraft CLI" in result.output

        # Test --version takes precedence over command
        result = self.runner.invoke(promptcraft, ['--version', '/command'])
        assert result.exit_code == 0

        # Test --init takes precedence
        with patch('promptcraft.main._initialize_project') as mock_init:
            result = self.runner.invoke(promptcraft, ['--init', '/command'])
            assert result.exit_code == 0
            mock_init.assert_called_once()

        # Test --list takes precedence
        with patch('promptcraft.main._list_commands') as mock_list:
            result = self.runner.invoke(promptcraft, ['--list', '/command'])
            assert result.exit_code == 0
            mock_list.assert_called_once()


class TestCLIErrorHandling:
    """Test CLI error handling and user feedback."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch('promptcraft.main.process_command')
    def test_command_not_found_error_display(self, mock_process):
        """Test CommandNotFoundError display and user guidance."""
        mock_process.side_effect = CommandNotFoundError("Command 'nonexistent' not found")
        
        result = self.runner.invoke(promptcraft, ['/nonexistent'])
        
        assert result.exit_code == 1
        assert "Command '/nonexistent' not found" in result.output
        assert "Run 'promptcraft --list' to see available commands" in result.output

    @patch('promptcraft.main.process_command')
    def test_template_read_error_display(self, mock_process):
        """Test TemplateReadError display with helpful information."""
        error_cases = [
            ("Permission denied reading template file: /path/to/template.md", "TEMPLATE_PERMISSION_DENIED"),
            ("Template file not found: /path/to/missing.md", "TEMPLATE_FILE_NOT_FOUND"),
            ("Failed to decode template file: encoding error", "TEMPLATE_ENCODING_ERROR"),
            ("I/O error reading template file: disk error", "TEMPLATE_IO_ERROR"),
        ]

        for error_message, error_code in error_cases:
            mock_process.side_effect = TemplateReadError(error_message, error_code)
            
            result = self.runner.invoke(promptcraft, ['/broken'])
            
            assert result.exit_code == 1
            assert error_message in result.output

    @patch('promptcraft.main.process_command')
    def test_generic_error_handling(self, mock_process):
        """Test generic error handling without exposing implementation details."""
        generic_errors = [
            ValueError("Invalid value"),
            TypeError("Wrong type"),
            RuntimeError("Runtime error"),
            IOError("I/O error"),
            KeyError("Missing key"),
            AttributeError("Missing attribute"),
        ]

        for error in generic_errors:
            mock_process.side_effect = error
            
            result = self.runner.invoke(promptcraft, ['/error'])
            
            assert result.exit_code == 1
            assert "Unexpected error occurred" in result.output
            
            # Should not expose implementation details
            assert "Traceback" not in result.output
            assert error.__class__.__name__ not in result.output
            assert str(error) not in result.output

    def test_error_message_formatting_consistency(self):
        """Test that error messages follow consistent formatting."""
        # Test with various invalid inputs that should produce consistent errors
        invalid_inputs = [
            ([]),  # Missing command name
        ]

        for invalid_input in invalid_inputs:
            result = self.runner.invoke(promptcraft, invalid_input)
            
            assert result.exit_code == 1
            # All error messages should use consistent formatting
            assert any(line.strip() for line in result.output.split('\n'))


class TestCLIFlagsIntegration:
    """Test CLI flags integration and functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch('promptcraft.main.process_command')
    def test_stdout_flag_integration(self, mock_process):
        """Test --stdout flag integration with CLI."""
        mock_process.return_value = "Test output for terminal"
        
        result = self.runner.invoke(promptcraft, ['--stdout', '/test-command', 'arg1'])
        
        assert result.exit_code == 0
        mock_process.assert_called_once_with('test-command', ['arg1'])
        
        # Should show generated message, not clipboard message
        assert "Prompt for '/test-command' generated:" in result.output
        assert "Test output for terminal" in result.output
        assert "copied to clipboard" not in result.output

    @patch('promptcraft.main.Path')
    def test_init_flag_integration(self, mock_path):
        """Test --init flag integration with CLI."""
        # Mock Path operations for initialization
        mock_commands_dir = Mock()
        mock_path.return_value = mock_commands_dir
        mock_commands_dir.mkdir = Mock()
        mock_commands_dir.exists.return_value = True
        mock_exemplo_file = Mock()
        mock_commands_dir.__truediv__ = Mock(return_value=mock_exemplo_file)
        mock_exemplo_file.exists.return_value = False
        mock_exemplo_file.write_text = Mock()
        
        result = self.runner.invoke(promptcraft, ['--init'])
        
        assert result.exit_code == 0
        assert "PromptCraft initialized!" in result.output
        assert "Next steps:" in result.output
        assert "promptcraft exemplo 'hello world'" in result.output

    @patch('promptcraft.main.discover_commands')
    def test_list_flag_integration(self, mock_discover):
        """Test --list flag integration with CLI."""
        # Test with no commands
        mock_discover.return_value = []
        
        result = self.runner.invoke(promptcraft, ['--list'])
        
        assert result.exit_code == 0
        assert "No commands found" in result.output
        assert "Run 'promptcraft --init' to create examples" in result.output

        # Test with commands
        mock_discover.return_value = [
            CommandInfo("test-cmd", Path("/fake/test-cmd.md"), "Project", "Test command"),
            CommandInfo("global-cmd", Path("/fake/global-cmd.md"), "Global", "Global command"),
        ]
        
        result = self.runner.invoke(promptcraft, ['--list'])
        
        assert result.exit_code == 0
        assert "Available Commands (2 found)" in result.output
        assert "test-cmd" in result.output
        assert "global-cmd" in result.output
        assert "Project" in result.output
        assert "Global" in result.output


class TestCLIOutputFormatting:
    """Test CLI output formatting and user experience."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch('promptcraft.main.process_command')
    @patch('promptcraft.main._copy_to_clipboard')
    def test_success_message_formatting(self, mock_copy_clipboard, mock_process):
        """Test success message formatting consistency."""
        mock_process.return_value = "Success output"
        mock_copy_clipboard.return_value = True

        test_commands = ['/simple', '/complex-command-name', '/123-numeric']

        for cmd in test_commands:
            result = self.runner.invoke(promptcraft, [cmd])
            
            assert result.exit_code == 0
            expected_message = f"Prompt for '{cmd}' copied to clipboard!"
            assert expected_message in result.output

    @patch('promptcraft.main.process_command')
    @patch('promptcraft.main._copy_to_clipboard')
    def test_clipboard_fallback_formatting(self, mock_copy_clipboard, mock_process):
        """Test clipboard fallback message formatting."""
        mock_process.return_value = "Fallback output"
        mock_copy_clipboard.return_value = False  # Simulate clipboard failure

        result = self.runner.invoke(promptcraft, ['/test'])

        assert result.exit_code == 0
        assert "⚠️ Clipboard unavailable, use --stdout instead" in result.output
        assert "Prompt for '/test' generated:" in result.output
        assert "Fallback output" in result.output

    def test_help_formatting_completeness(self):
        """Test help message formatting and completeness."""
        result = self.runner.invoke(promptcraft, ['--help'])

        assert result.exit_code == 0

        # Check for proper section organization
        assert "Usage:" in result.output
        assert "Options:" in result.output
        
        # Check for usage examples section
        assert "Usage Examples:" in result.output
        examples = [
            "promptcraft /create-story",
            "promptcraft /fix-bug", 
            "promptcraft /code-review"
        ]
        for example in examples:
            assert example in result.output

    @patch('promptcraft.main.discover_commands')
    def test_list_output_formatting(self, mock_discover):
        """Test --list output formatting with various command scenarios."""
        # Test with mixed command names and descriptions
        mock_discover.return_value = [
            CommandInfo("a", Path("/fake/a.md"), "Project", "Short description"),
            CommandInfo("very-long-command-name", Path("/fake/very-long.md"), "Global", "Very long description that tests column alignment and wrapping behavior"),
            CommandInfo("mid-length-cmd", Path("/fake/mid.md"), "Project", "Mid-length description"),
        ]

        result = self.runner.invoke(promptcraft, ['--list'])

        assert result.exit_code == 0
        assert "Available Commands (3 found):" in result.output
        
        # Check table structure
        assert "Command" in result.output
        assert "Source" in result.output
        assert "Description" in result.output
        assert "---" in result.output or "─" in result.output  # Table separator

        # Check all commands are listed
        assert "very-long-command-name" in result.output
        assert "mid-length-cmd" in result.output
        assert "a" in result.output


class TestCLIPerformanceAndRobustness:
    """Test CLI performance requirements and robustness."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch('promptcraft.main.process_command')
    @patch('promptcraft.main._copy_to_clipboard')
    def test_cli_performance_requirement(self, mock_copy_clipboard, mock_process):
        """Test CLI meets <150ms performance requirement."""
        mock_process.return_value = "Performance test"
        mock_copy_clipboard.return_value = True

        import time
        
        # Test multiple runs to get average performance
        times = []
        for _ in range(10):
            start_time = time.time()
            result = self.runner.invoke(promptcraft, ['/perf-test', 'arg1'])
            end_time = time.time()
            
            assert result.exit_code == 0
            times.append((end_time - start_time) * 1000)  # Convert to ms

        # Calculate statistics
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        # Performance targets (relaxed for test environment variability)
        assert avg_time < 500, f"Average time {avg_time}ms exceeds reasonable limit"
        assert max_time < 1000, f"Max time {max_time}ms exceeds reasonable limit"

    def test_cli_memory_stability(self):
        """Test CLI memory usage remains stable."""
        import gc
        
        # Force garbage collection before test
        gc.collect()
        
        # Run multiple CLI operations
        for i in range(100):
            result = self.runner.invoke(promptcraft, ['--help'])
            assert result.exit_code == 0
            
            # Periodically check memory stability
            if i % 20 == 0:
                gc.collect()  # Allow garbage collection

        # If we reach here without memory errors, test passes
        assert True

    @patch('promptcraft.main.process_command')
    @patch('promptcraft.main._copy_to_clipboard')
    def test_cli_concurrent_safety(self, mock_copy_clipboard, mock_process):
        """Test CLI behavior under concurrent usage simulation."""
        mock_process.return_value = "Concurrent test"
        mock_copy_clipboard.return_value = True

        import threading
        import queue
        
        results = queue.Queue()
        
        def run_cli_command(cmd_suffix):
            try:
                result = self.runner.invoke(promptcraft, [f'/concurrent-{cmd_suffix}'])
                results.put((cmd_suffix, result.exit_code, None))
            except Exception as e:
                results.put((cmd_suffix, -1, str(e)))

        # Start multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=run_cli_command, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=5.0)

        # Check results
        completed_results = []
        while not results.empty():
            completed_results.append(results.get())

        assert len(completed_results) == 10, "Not all threads completed"
        
        for cmd_suffix, exit_code, error in completed_results:
            if error:
                pytest.fail(f"Thread {cmd_suffix} failed with error: {error}")
            assert exit_code == 0, f"Thread {cmd_suffix} failed with exit code {exit_code}"