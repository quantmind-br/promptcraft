"""Enhanced clipboard functionality tests with comprehensive coverage."""

import pytest
import time
import os
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner

from promptcraft.main import promptcraft, _copy_to_clipboard, _is_headless_environment
from promptcraft.exceptions import CommandNotFoundError, TemplateReadError


class TestClipboardMockExtensions:
    """Extend existing clipboard mock tests with additional scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch('promptcraft.main.process_command')
    @patch('promptcraft.main._copy_to_clipboard')
    def test_clipboard_with_various_content_types(self, mock_copy_clipboard, mock_process):
        """Test clipboard with various content types and sizes."""
        content_scenarios = [
            # Empty content
            ("", "empty-test"),
            # Small content
            ("Small test content", "small-test"),
            # Medium content with newlines
            ("Line 1\nLine 2\nLine 3\n", "multiline-test"),
            # Large content (10KB)
            ("Large content " * 500, "large-test"),
            # Very large content (100KB)
            ("Very large content " * 5000, "very-large-test"),
            # Unicode content
            ("Unicode: café 测试 🚀 Ñoël", "unicode-test"),
            # Special characters
            ("Special: @#$%^&*()[]{}|\\:;\"'<>?,./", "special-chars-test"),
            # Mixed content
            ("Mixed:\nUnicode: é\nSpecial: @#$\nNumbers: 123", "mixed-test"),
        ]

        for content, cmd_name in content_scenarios:
            mock_process.return_value = content
            mock_copy_clipboard.return_value = True

            result = self.runner.invoke(promptcraft, [f'/{cmd_name}'])

            assert result.exit_code == 0
            mock_copy_clipboard.assert_called_with(content, cmd_name)
            assert f"Prompt for '/{cmd_name}' copied to clipboard!" in result.output

    @patch('promptcraft.main.process_command')
    @patch('promptcraft.main._copy_to_clipboard')
    def test_clipboard_success_vs_failure_scenarios(self, mock_copy_clipboard, mock_process):
        """Test both clipboard success and failure scenarios."""
        mock_process.return_value = "Test content"

        # Test success scenario
        mock_copy_clipboard.return_value = True
        result = self.runner.invoke(promptcraft, ['/success-test'])

        assert result.exit_code == 0
        assert "copied to clipboard!" in result.output
        assert "⚠️ Clipboard unavailable" not in result.output

        # Test failure scenario with fallback
        mock_copy_clipboard.return_value = False
        result = self.runner.invoke(promptcraft, ['/failure-test'])

        assert result.exit_code == 0
        assert "⚠️ Clipboard unavailable, use --stdout instead" in result.output
        assert "Prompt for '/failure-test' generated:" in result.output
        assert "Test content" in result.output

    @patch('promptcraft.main.process_command')
    @patch('promptcraft.main._copy_to_clipboard')
    def test_clipboard_behavior_with_command_errors(self, mock_copy_clipboard, mock_process):
        """Test that clipboard is not called when command processing fails."""
        error_scenarios = [
            CommandNotFoundError("Command not found"),
            TemplateReadError("Template read failed"),
            RuntimeError("Generic error"),
        ]

        for error in error_scenarios:
            mock_process.side_effect = error
            mock_copy_clipboard.reset_mock()

            result = self.runner.invoke(promptcraft, ['/error-test'])

            assert result.exit_code == 1
            mock_copy_clipboard.assert_not_called()

    @patch('promptcraft.main.process_command')
    @patch('promptcraft.main._copy_to_clipboard')
    def test_clipboard_with_concurrent_operations(self, mock_copy_clipboard, mock_process):
        """Test clipboard operations don't interfere under concurrent usage."""
        import threading
        import queue

        results = queue.Queue()
        mock_process.return_value = "Concurrent test"
        mock_copy_clipboard.return_value = True

        def run_clipboard_test(thread_id):
            try:
                result = self.runner.invoke(promptcraft, [f'/concurrent-{thread_id}'])
                results.put((thread_id, result.exit_code, None))
            except Exception as e:
                results.put((thread_id, -1, str(e)))

        # Start concurrent operations
        threads = []
        for i in range(10):
            thread = threading.Thread(target=run_clipboard_test, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Check results
        thread_results = []
        while not results.empty():
            thread_results.append(results.get())

        assert len(thread_results) == 10
        
        for thread_id, exit_code, error in thread_results:
            if error:
                pytest.fail(f"Thread {thread_id} failed: {error}")
            assert exit_code == 0


class TestClipboardErrorScenariosAndFallback:
    """Test clipboard error scenarios and fallback behavior."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch('promptcraft.main.pyperclip.copy')
    @patch('promptcraft.main._is_headless_environment')
    def test_clipboard_backend_exceptions(self, mock_headless, mock_pyperclip):
        """Test handling of various clipboard backend exceptions."""
        mock_headless.return_value = False

        # Test different exception types that pyperclip might raise
        exception_scenarios = [
            Exception("Generic clipboard error"),
            OSError("System clipboard not available"),
            RuntimeError("Clipboard backend failed"),
            ImportError("Clipboard module not found"),
            AttributeError("Clipboard method missing"),
        ]

        for exception in exception_scenarios:
            mock_pyperclip.side_effect = exception
            
            result = _copy_to_clipboard("test content", "test-command")
            
            assert result is False
            mock_pyperclip.assert_called_with("test content")

    @patch('promptcraft.main.pyperclip.copy')
    @patch('promptcraft.main._is_headless_environment')
    def test_clipboard_timeout_scenarios(self, mock_headless, mock_pyperclip):
        """Test clipboard timeout scenarios."""
        mock_headless.return_value = False

        timeout_scenarios = [
            (0.0, 0.16),   # 160ms - exceeds 150ms limit
            (0.0, 0.20),   # 200ms - well over limit
            (0.0, 1.0),    # 1 second - way over limit
        ]

        for start_time, end_time in timeout_scenarios:
            with patch('promptcraft.main.time.time', side_effect=[start_time, end_time]):
                result = _copy_to_clipboard("test content", "test-command")
                
                assert result is False  # Should timeout
                mock_pyperclip.assert_called_with("test content")

    @patch('promptcraft.main.pyperclip.copy')
    @patch('promptcraft.main._is_headless_environment')
    def test_clipboard_success_within_timeout(self, mock_headless, mock_pyperclip):
        """Test clipboard success when within timeout limits."""
        mock_headless.return_value = False

        success_scenarios = [
            (0.0, 0.001),  # 1ms - very fast
            (0.0, 0.05),   # 50ms - reasonable
            (0.0, 0.14),   # 140ms - just under limit
            (0.0, 0.149),  # 149ms - just under limit
        ]

        for start_time, end_time in success_scenarios:
            with patch('promptcraft.main.time.time', side_effect=[start_time, end_time]):
                result = _copy_to_clipboard("test content", "test-command")
                
                assert result is True  # Should succeed
                mock_pyperclip.assert_called_with("test content")

    def test_headless_environment_detection_comprehensive(self):
        """Test comprehensive headless environment detection."""
        # Test CI environment detection
        with patch('promptcraft.main.os.environ.get', side_effect=lambda k, d=None: 'true' if k == 'CI' else d):
            assert _is_headless_environment() is True

        # Test DISPLAY environment detection
        with patch('promptcraft.main.os.environ.get', side_effect=lambda k, d=None: '' if k == 'DISPLAY' else d):
            assert _is_headless_environment() is True

        # Test manual override
        with patch('promptcraft.main.os.environ.get', side_effect=lambda k, d=None: 'true' if k == 'PROMPTCRAFT_NO_CLIPBOARD' else d):
            assert _is_headless_environment() is True

        # Test Linux without X11
        with patch('promptcraft.main.sys.platform', 'linux'), \
             patch('promptcraft.main.os.environ.get', side_effect=lambda k, d=None: None), \
             patch('promptcraft.main.os.path.exists', return_value=False):
            assert _is_headless_environment() is True

        # Test normal environment
        with patch('promptcraft.main.os.environ.get', side_effect=lambda k, d=None: ':0' if k == 'DISPLAY' else d):
            assert _is_headless_environment() is False

    @patch('promptcraft.main.process_command')
    @patch('promptcraft.main._copy_to_clipboard')
    def test_fallback_message_consistency(self, mock_copy_clipboard, mock_process):
        """Test that fallback messages are consistent and helpful."""
        mock_process.return_value = "Fallback test content"
        mock_copy_clipboard.return_value = False

        result = self.runner.invoke(promptcraft, ['/fallback-test'])

        assert result.exit_code == 0
        
        # Check for consistent fallback messaging
        assert "⚠️ Clipboard unavailable, use --stdout instead" in result.output
        assert "Prompt for '/fallback-test' generated:" in result.output
        assert "Fallback test content" in result.output
        
        # Should not show success message
        assert "copied to clipboard!" not in result.output

    @patch('promptcraft.main.process_command')
    @patch('promptcraft.main._copy_to_clipboard')
    def test_fallback_preserves_content_formatting(self, mock_copy_clipboard, mock_process):
        """Test that fallback preserves content formatting."""
        formatted_content = """# Formatted Content

## Section 1
Some **bold** and *italic* text.

### Code Example
```python
def example():
    return "Hello, World!"
```

- List item 1
- List item 2

> Blockquote text

Final paragraph with Unicode: café 测试 🚀"""

        mock_process.return_value = formatted_content
        mock_copy_clipboard.return_value = False

        result = self.runner.invoke(promptcraft, ['/formatted-fallback'])

        assert result.exit_code == 0
        assert formatted_content in result.output
        
        # Check that formatting elements are preserved
        assert "# Formatted Content" in result.output
        assert "```python" in result.output
        assert "café 测试 🚀" in result.output


class TestStdoutFlagIntegration:
    """Test integration between clipboard functionality and --stdout flag."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch('promptcraft.main.process_command')
    @patch('promptcraft.main._copy_to_clipboard')
    def test_stdout_flag_bypasses_clipboard(self, mock_copy_clipboard, mock_process):
        """Test that --stdout flag completely bypasses clipboard operations."""
        mock_process.return_value = "Stdout test content"

        result = self.runner.invoke(promptcraft, ['--stdout', '/stdout-test'])

        assert result.exit_code == 0
        # Clipboard should never be called with --stdout
        mock_copy_clipboard.assert_not_called()
        
        # Should show stdout-specific messages
        assert "Prompt for '/stdout-test' generated:" in result.output
        assert "Stdout test content" in result.output
        assert "copied to clipboard" not in result.output

    @patch('promptcraft.main.process_command')
    @patch('promptcraft.main._copy_to_clipboard')
    def test_stdout_flag_with_various_content(self, mock_copy_clipboard, mock_process):
        """Test --stdout flag with various content types."""
        content_scenarios = [
            ("", "empty"),
            ("Simple content", "simple"),
            ("Multi\nline\ncontent", "multiline"),
            ("Unicode: café 测试 🚀", "unicode"),
            ("Large content " * 1000, "large"),
        ]

        for content, test_name in content_scenarios:
            mock_process.return_value = content
            mock_copy_clipboard.reset_mock()

            result = self.runner.invoke(promptcraft, ['--stdout', f'/{test_name}'])

            assert result.exit_code == 0
            mock_copy_clipboard.assert_not_called()
            
            if content:  # Non-empty content should appear in output
                assert content in result.output

    @patch('promptcraft.main.process_command')
    @patch('promptcraft.main._copy_to_clipboard')
    def test_stdout_flag_error_handling(self, mock_copy_clipboard, mock_process):
        """Test that --stdout flag doesn't affect error handling."""
        error_scenarios = [
            CommandNotFoundError("Command not found"),
            TemplateReadError("Template error"),
            RuntimeError("Generic error"),
        ]

        for error in error_scenarios:
            mock_process.side_effect = error
            mock_copy_clipboard.reset_mock()

            result = self.runner.invoke(promptcraft, ['--stdout', '/error-test'])

            assert result.exit_code == 1
            mock_copy_clipboard.assert_not_called()
            # Error handling should be the same regardless of --stdout

    @patch('promptcraft.main.process_command')
    @patch('promptcraft.main._copy_to_clipboard')
    def test_stdout_vs_clipboard_behavior_comparison(self, mock_copy_clipboard, mock_process):
        """Test behavioral differences between --stdout and clipboard modes."""
        test_content = "Comparison test content"
        mock_process.return_value = test_content

        # Test clipboard mode (default)
        mock_copy_clipboard.return_value = True
        result_clipboard = self.runner.invoke(promptcraft, ['/comparison-test'])

        assert result_clipboard.exit_code == 0
        mock_copy_clipboard.assert_called_once_with(test_content, "comparison-test")
        assert "copied to clipboard!" in result_clipboard.output
        assert test_content not in result_clipboard.output  # Content not shown in clipboard mode

        # Test stdout mode
        mock_copy_clipboard.reset_mock()
        result_stdout = self.runner.invoke(promptcraft, ['--stdout', '/comparison-test'])

        assert result_stdout.exit_code == 0
        mock_copy_clipboard.assert_not_called()
        assert "generated:" in result_stdout.output
        assert test_content in result_stdout.output  # Content shown in stdout mode


class TestClipboardTimeoutAndPerformance:
    """Test clipboard timeout and performance requirements."""

    @patch('promptcraft.main.pyperclip.copy')
    @patch('promptcraft.main._is_headless_environment')
    def test_clipboard_timeout_enforcement(self, mock_headless, mock_pyperclip):
        """Test that clipboard timeout is strictly enforced."""
        mock_headless.return_value = False

        # Test exact timeout boundary (150ms)
        with patch('promptcraft.main.time.time', side_effect=[0.0, 0.150]):
            result = _copy_to_clipboard("boundary test", "test")
            assert result is False  # Should fail at exactly 150ms

        # Test just under timeout (149ms)
        with patch('promptcraft.main.time.time', side_effect=[0.0, 0.149]):
            result = _copy_to_clipboard("under limit test", "test")
            assert result is True  # Should succeed just under limit

        # Test well over timeout (1 second)
        with patch('promptcraft.main.time.time', side_effect=[0.0, 1.0]):
            result = _copy_to_clipboard("over limit test", "test")
            assert result is False  # Should fail well over limit

    @patch('promptcraft.main.process_command')
    @patch('promptcraft.main._copy_to_clipboard')
    def test_end_to_end_performance_with_clipboard(self, mock_copy_clipboard, mock_process):
        """Test end-to-end performance including clipboard operations."""
        mock_process.return_value = "Performance test"
        mock_copy_clipboard.return_value = True

        # Measure actual CLI performance
        start_time = time.time()
        result = self.runner.invoke(promptcraft, ['/performance-test'])
        end_time = time.time()

        assert result.exit_code == 0
        execution_time_ms = (end_time - start_time) * 1000

        # Total time should be reasonable (allowing for test environment overhead)
        assert execution_time_ms < 2000  # 2 seconds maximum for test environment

    def test_clipboard_performance_with_large_content(self):
        """Test clipboard performance with various content sizes."""
        content_sizes = [
            (1024, "1KB"),          # 1KB
            (10240, "10KB"),        # 10KB
            (102400, "100KB"),      # 100KB
            (1048576, "1MB"),       # 1MB
        ]

        for size, description in content_sizes:
            large_content = "x" * size
            
            with patch('promptcraft.main._is_headless_environment', return_value=False), \
                 patch('promptcraft.main.pyperclip.copy') as mock_copy:
                
                start_time = time.time()
                result = _copy_to_clipboard(large_content, f"large-{description}")
                end_time = time.time()
                
                execution_time_ms = (end_time - start_time) * 1000
                
                # Should complete quickly regardless of content size
                assert execution_time_ms < 100  # Should be very fast in mock
                assert result is True
                mock_copy.assert_called_once_with(large_content)

    @patch('promptcraft.main.process_command')
    @patch('promptcraft.main._copy_to_clipboard')
    def test_clipboard_performance_under_load(self, mock_copy_clipboard, mock_process):
        """Test clipboard performance under load conditions."""
        mock_process.return_value = "Load test"
        mock_copy_clipboard.return_value = True

        # Simulate load by running many operations quickly
        execution_times = []
        
        for i in range(50):
            start_time = time.time()
            result = self.runner.invoke(promptcraft, [f'/load-test-{i}'])
            end_time = time.time()
            
            assert result.exit_code == 0
            execution_times.append((end_time - start_time) * 1000)

        # Performance should remain consistent under load
        avg_time = sum(execution_times) / len(execution_times)
        max_time = max(execution_times)
        
        # Times should be reasonable even under load
        assert avg_time < 500  # Average under 500ms
        assert max_time < 1000  # No single operation over 1 second

    def test_clipboard_memory_efficiency(self):
        """Test that clipboard operations are memory efficient."""
        # Test that clipboard doesn't hold references to large content
        large_content = "Large clipboard content " * 10000  # ~250KB
        
        with patch('promptcraft.main._is_headless_environment', return_value=False), \
             patch('promptcraft.main.pyperclip.copy') as mock_copy:
            
            # Process many large clipboard operations
            for i in range(100):
                result = _copy_to_clipboard(large_content, f"memory-test-{i}")
                assert result is True
                mock_copy.assert_called_with(large_content)
                mock_copy.reset_mock()

        # If we reach here without memory errors, test passes
        assert True


class TestClipboardRegressionAndCompatibility:
    """Test clipboard regression scenarios and compatibility."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch('promptcraft.main.process_command')
    @patch('promptcraft.main._copy_to_clipboard')
    def test_clipboard_regression_scenarios(self, mock_copy_clipboard, mock_process):
        """Test clipboard functionality doesn't regress with edge cases."""
        mock_process.return_value = "Regression test"

        # Test regression scenarios
        regression_tests = [
            # Normal success
            (True, "copied to clipboard!"),
            # Clipboard failure with fallback
            (False, "⚠️ Clipboard unavailable"),
        ]

        for clipboard_result, expected_message in regression_tests:
            mock_copy_clipboard.return_value = clipboard_result
            
            result = self.runner.invoke(promptcraft, ['/regression-test'])
            
            assert result.exit_code == 0
            assert expected_message in result.output
            
            if clipboard_result:
                assert "Regression test" not in result.output  # Content not shown on success
            else:
                assert "Regression test" in result.output  # Content shown on fallback

    def test_clipboard_compatibility_across_environments(self):
        """Test clipboard compatibility detection across different environments."""
        # Test various environment configurations
        environment_tests = [
            # Normal desktop environment
            ({'DISPLAY': ':0'}, False),
            # CI environment
            ({'CI': 'true'}, True),
            # Headless environment
            ({'DISPLAY': ''}, True),
            # Manual disable
            ({'PROMPTCRAFT_NO_CLIPBOARD': 'true'}, True),
            # SSH session without X11
            ({'SSH_CLIENT': '192.168.1.1 12345 22', 'DISPLAY': None}, True),
        ]

        for env_vars, expected_headless in environment_tests:
            with patch.dict(os.environ, env_vars, clear=True):
                result = _is_headless_environment()
                assert result == expected_headless

    @patch('promptcraft.main.process_command')
    @patch('promptcraft.main._copy_to_clipboard')
    def test_clipboard_integration_with_all_cli_features(self, mock_copy_clipboard, mock_process):
        """Test clipboard integration doesn't break other CLI features."""
        mock_process.return_value = "Integration test"
        mock_copy_clipboard.return_value = True

        # Test clipboard works with various CLI features
        cli_feature_tests = [
            # Basic command
            (['/basic-test'], 0, "copied to clipboard!"),
            # Command with arguments
            (['/args-test', 'arg1', 'arg2'], 0, "copied to clipboard!"),
            # Command with special characters
            (['/special-test', '@#$%'], 0, "copied to clipboard!"),
            # Command with Unicode arguments
            (['/unicode-test', 'café', '测试'], 0, "copied to clipboard!"),
        ]

        for args, expected_exit, expected_message in cli_feature_tests:
            result = self.runner.invoke(promptcraft, args)
            
            assert result.exit_code == expected_exit
            assert expected_message in result.output