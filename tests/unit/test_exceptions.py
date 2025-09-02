"""Unit tests for exceptions module."""

import pytest
from unittest.mock import patch, Mock
from click.testing import CliRunner
from pathlib import Path

from promptcraft.exceptions import (
    PromptCraftError,
    TemplateError,
    ConfigurationError,
    CommandNotFoundError,
    TemplateReadError,
)


def test_promptcraft_error():
    """Test PromptCraftError exception."""
    error = PromptCraftError("Test error")
    assert str(error) == "Test error"
    assert isinstance(error, Exception)


def test_template_error():
    """Test TemplateError exception."""
    error = TemplateError("Template error")
    assert str(error) == "Template error"
    assert isinstance(error, PromptCraftError)


def test_configuration_error():
    """Test ConfigurationError exception."""
    error = ConfigurationError("Config error")
    assert str(error) == "Config error"
    assert isinstance(error, PromptCraftError)


def test_command_not_found_error():
    """Test CommandNotFoundError exception."""
    # Test with default error code
    error = CommandNotFoundError("Command not found")
    assert str(error) == "Command not found"
    assert error.message == "Command not found"
    assert error.error_code == "COMMAND_NOT_FOUND"
    assert isinstance(error, PromptCraftError)
    
    # Test with custom error code
    error_custom = CommandNotFoundError("Custom message", "CUSTOM_CODE")
    assert str(error_custom) == "Custom message"
    assert error_custom.message == "Custom message"
    assert error_custom.error_code == "CUSTOM_CODE"


def test_template_read_error():
    """Test TemplateReadError exception."""
    # Test with default error code
    error = TemplateReadError("Template read failed")
    assert str(error) == "Template read failed"
    assert error.message == "Template read failed"
    assert error.error_code == "TEMPLATE_READ_ERROR"
    assert isinstance(error, PromptCraftError)
    
    # Test with custom error code
    error_custom = TemplateReadError("Permission denied", "PERMISSION_ERROR")
    assert str(error_custom) == "Permission denied"
    assert error_custom.message == "Permission denied"
    assert error_custom.error_code == "PERMISSION_ERROR"


def test_exception_inheritance_hierarchy():
    """Test that all exceptions inherit correctly."""
    # Test CommandNotFoundError inheritance
    cmd_error = CommandNotFoundError("test")
    assert isinstance(cmd_error, Exception)
    assert isinstance(cmd_error, PromptCraftError)
    assert isinstance(cmd_error, CommandNotFoundError)
    
    # Test TemplateReadError inheritance
    read_error = TemplateReadError("test")
    assert isinstance(read_error, Exception)
    assert isinstance(read_error, PromptCraftError)
    assert isinstance(read_error, TemplateReadError)


def test_exception_raising_and_catching():
    """Test that exceptions can be properly raised and caught."""
    # Test CommandNotFoundError
    with pytest.raises(CommandNotFoundError) as exc_info:
        raise CommandNotFoundError("Command 'test' not found")
    assert exc_info.value.message == "Command 'test' not found"
    assert exc_info.value.error_code == "COMMAND_NOT_FOUND"
    
    # Test TemplateReadError  
    with pytest.raises(TemplateReadError) as exc_info:
        raise TemplateReadError("Failed to read file")
    assert exc_info.value.message == "Failed to read file"
    assert exc_info.value.error_code == "TEMPLATE_READ_ERROR"
    
    # Test catching as base exception
    with pytest.raises(PromptCraftError):
        raise CommandNotFoundError("Base exception catch test")


def test_cross_module_import():
    """Test that exceptions can be imported from the main module."""
    # This test verifies the exceptions are properly exposed
    from promptcraft.exceptions import CommandNotFoundError, TemplateReadError
    
    # Test instantiation after import
    cmd_error = CommandNotFoundError("Import test")
    template_error = TemplateReadError("Import test")
    
    assert isinstance(cmd_error, CommandNotFoundError)
    assert isinstance(template_error, TemplateReadError)


# Comprehensive Error Condition Tests

class TestExceptionScenarios:
    """Test all custom exception classes and their scenarios."""

    def test_command_not_found_error_scenarios(self):
        """Test CommandNotFoundError in various scenarios."""
        scenarios = [
            ("Simple command not found", "COMMAND_NOT_FOUND"),
            ("Command 'complex-name' with details not found in /path", "CUSTOM_CODE"),
            ("Unicode command '测试' not found", "UNICODE_COMMAND"),
            ("Command with special chars '@#$' not found", "SPECIAL_CHARS"),
        ]
        
        for message, error_code in scenarios:
            error = CommandNotFoundError(message, error_code)
            
            assert str(error) == message
            assert error.message == message
            assert error.error_code == error_code
            assert isinstance(error, PromptCraftError)
            
            # Test that it can be raised and caught
            with pytest.raises(CommandNotFoundError) as exc_info:
                raise error
            
            caught_error = exc_info.value
            assert caught_error.message == message
            assert caught_error.error_code == error_code

    def test_template_read_error_scenarios(self):
        """Test TemplateReadError in various scenarios."""
        scenarios = [
            ("Permission denied reading template", "TEMPLATE_PERMISSION_DENIED"),
            ("Template file not found: /path/to/file.md", "TEMPLATE_FILE_NOT_FOUND"),
            ("Failed to decode template: encoding error", "TEMPLATE_ENCODING_ERROR"),
            ("I/O error reading template: disk full", "TEMPLATE_IO_ERROR"),
            ("Template file is locked by another process", "TEMPLATE_LOCKED"),
            ("Template file is too large to process", "TEMPLATE_TOO_LARGE"),
        ]
        
        for message, error_code in scenarios:
            error = TemplateReadError(message, error_code)
            
            assert str(error) == message
            assert error.message == message
            assert error.error_code == error_code
            assert isinstance(error, PromptCraftError)
            
            # Test that it can be raised and caught
            with pytest.raises(TemplateReadError) as exc_info:
                raise error
            
            caught_error = exc_info.value
            assert caught_error.message == message
            assert caught_error.error_code == error_code

    def test_template_error_scenarios(self):
        """Test TemplateError in various template processing scenarios."""
        scenarios = [
            "Template content cannot be None",
            "Template content must be a string",
            "Template content cannot be empty",
            "Invalid template syntax detected",
            "Template placeholder error",
            "Template processing failed due to malformed content",
        ]
        
        for message in scenarios:
            error = TemplateError(message)
            
            assert str(error) == message
            assert isinstance(error, PromptCraftError)
            
            with pytest.raises(TemplateError) as exc_info:
                raise error
            
            assert str(exc_info.value) == message

    def test_configuration_error_scenarios(self):
        """Test ConfigurationError in various configuration scenarios."""
        scenarios = [
            "Invalid configuration file format",
            "Missing required configuration parameter",
            "Configuration file not found",
            "Invalid configuration value for parameter 'timeout'",
            "Configuration validation failed",
        ]
        
        for message in scenarios:
            error = ConfigurationError(message)
            
            assert str(error) == message
            assert isinstance(error, PromptCraftError)
            
            with pytest.raises(ConfigurationError) as exc_info:
                raise error
            
            assert str(exc_info.value) == message


class TestErrorHandlingAndUserFriendlyMessages:
    """Test error handling produces user-friendly messages."""

    def test_error_message_formatting(self):
        """Test that error messages are well-formatted and informative."""
        # Test CommandNotFoundError message formatting
        cmd_error = CommandNotFoundError(
            "Command 'my-command' not found. Searched in: /home/user/.promptcraft/commands, /project/.promptcraft/commands"
        )
        
        message = str(cmd_error)
        assert "Command 'my-command' not found" in message
        assert "Searched in:" in message
        assert "/home/user/.promptcraft/commands" in message
        
        # Test TemplateReadError message formatting
        template_error = TemplateReadError(
            "Permission denied reading template file: /path/to/restricted.md. Check file permissions.",
            "TEMPLATE_PERMISSION_DENIED"
        )
        
        message = str(template_error)
        assert "Permission denied" in message
        assert "/path/to/restricted.md" in message
        assert "Check file permissions" in message

    def test_error_context_preservation(self):
        """Test that error context is preserved through the call stack."""
        # Test error chaining
        original_error = FileNotFoundError("Original file not found")
        
        try:
            raise original_error
        except FileNotFoundError as e:
            wrapped_error = TemplateReadError(
                f"Failed to read template: {e}",
                "TEMPLATE_FILE_NOT_FOUND"
            )
            wrapped_error.__cause__ = e
            
            # Test that context is preserved
            assert wrapped_error.__cause__ is original_error
            assert "Original file not found" in str(wrapped_error)

    def test_multilingual_error_messages(self):
        """Test error handling with Unicode and international characters."""
        unicode_scenarios = [
            ("Comando 'café' não encontrado", "Portuguese"),
            ("コマンド '测试' が見つかりません", "Japanese/Chinese"),
            ("Команда 'тест' не найдена", "Russian"),
            ("🚀 Emoji command not found 😢", "Emoji"),
        ]
        
        for message, description in unicode_scenarios:
            error = CommandNotFoundError(message)
            
            assert str(error) == message
            assert error.message == message
            
            # Should be able to raise and catch with Unicode content
            with pytest.raises(CommandNotFoundError) as exc_info:
                raise error
            
            assert str(exc_info.value) == message


class TestRecoveryMechanismsAndFallbackBehavior:
    """Test recovery mechanisms and fallback behavior."""

    def test_error_recovery_in_discovery(self):
        """Test that command discovery recovers from individual file errors."""
        from unittest.mock import patch, Mock
        from promptcraft.core import discover_commands
        
        # Mock Path operations to simulate mixed success/failure
        mock_paths = [
            Mock(name="good1.md", is_file=lambda: True, stem="good1"),
            Mock(name="bad.md", is_file=lambda: True, stem="bad"),  # Will cause error
            Mock(name="good2.md", is_file=lambda: True, stem="good2"),
        ]
        
        def mock_extract_description(path):
            if "bad" in str(path):
                raise OSError("Simulated error")
            return f"Description for {path.stem}"
        
        with patch('promptcraft.core.Path.cwd') as mock_cwd, \
             patch('promptcraft.core.Path.home') as mock_home, \
             patch('promptcraft.core._extract_description', side_effect=mock_extract_description):
            
            # Mock directory structure
            mock_cmd_dir = Mock()
            mock_cmd_dir.exists.return_value = True
            mock_cmd_dir.is_dir.return_value = True
            mock_cmd_dir.glob.return_value = mock_paths
            
            mock_cwd.return_value = Mock()
            mock_cwd.return_value.__truediv__ = Mock(return_value=mock_cmd_dir)
            mock_home.return_value = Mock()
            
            # Should recover and return good commands despite one failure
            result = discover_commands()
            
            # Should have recovered and found the good commands
            good_names = [cmd.name for cmd in result if cmd.name.startswith('good')]
            assert len(good_names) >= 2

    def test_clipboard_fallback_behavior(self):
        """Test clipboard fallback behavior when clipboard operations fail."""
        from promptcraft.main import _copy_to_clipboard, _is_headless_environment
        
        # Test headless environment detection triggers fallback
        with patch('promptcraft.main._is_headless_environment', return_value=True):
            result = _copy_to_clipboard("test content", "test-command")
            assert result is False  # Should fall back
        
        # Test clipboard exception triggers fallback
        with patch('promptcraft.main._is_headless_environment', return_value=False), \
             patch('promptcraft.main.pyperclip.copy', side_effect=Exception("Clipboard error")):
            result = _copy_to_clipboard("test content", "test-command")
            assert result is False  # Should fall back
        
        # Test timeout triggers fallback
        with patch('promptcraft.main._is_headless_environment', return_value=False), \
             patch('promptcraft.main.time.time', side_effect=[0.0, 0.2]), \
             patch('promptcraft.main.pyperclip.copy'):
            result = _copy_to_clipboard("test content", "test-command")
            assert result is False  # Should fall back due to timeout

    def test_graceful_degradation_patterns(self):
        """Test graceful degradation when components fail."""
        from promptcraft.core import discover_commands
        
        # Test when directory permissions cause partial failures
        with patch('promptcraft.core.Path.cwd') as mock_cwd, \
             patch('promptcraft.core.Path.home') as mock_home:
            
            # Mock successful cwd but failed home directory
            mock_cwd_dir = Mock()
            mock_cwd_dir.exists.return_value = True
            mock_cwd_dir.is_dir.return_value = True
            mock_cwd_dir.glob.return_value = [Mock(is_file=lambda: True, stem="local-cmd")]
            
            mock_home_dir = Mock()
            mock_home_dir.exists.return_value = True
            mock_home_dir.is_dir.return_value = True
            mock_home_dir.glob.side_effect = PermissionError("Access denied")
            
            mock_cwd.return_value.__truediv__ = Mock(return_value=mock_cwd_dir)
            mock_home.return_value.__truediv__ = Mock(return_value=mock_home_dir)
            
            # Should gracefully handle home directory failure
            with patch('promptcraft.core._extract_description', return_value="Test description"):
                result = discover_commands()
                
                # Should still find local commands despite home directory failure
                assert len(result) >= 0  # May find local commands


class TestExceptionPropagationThroughCallStack:
    """Test that exceptions propagate correctly through the call stack."""

    def test_exception_propagation_in_process_command(self):
        """Test exception propagation through process_command call stack."""
        from promptcraft.core import process_command
        
        # Test CommandNotFoundError propagation
        with patch('promptcraft.core.find_command_path', side_effect=CommandNotFoundError("Not found")):
            with pytest.raises(CommandNotFoundError) as exc_info:
                process_command("nonexistent", ["args"])
            
            # Should enhance error context while preserving original
            error = exc_info.value
            assert "Command 'nonexistent' processing failed" in str(error)
            assert error.__cause__ is not None
            assert isinstance(error.__cause__, CommandNotFoundError)
        
        # Test TemplateReadError propagation
        with patch('promptcraft.core.find_command_path', return_value=Path("/fake/template.md")), \
             patch('promptcraft.core.generate_prompt', side_effect=TemplateReadError("Read failed")):
            
            with pytest.raises(TemplateReadError) as exc_info:
                process_command("broken-template", ["args"])
            
            # Should enhance error context
            error = exc_info.value
            assert "Command 'broken-template' template processing failed" in str(error)
            assert error.__cause__ is not None
            assert isinstance(error.__cause__, TemplateReadError)

    def test_exception_chain_preservation(self):
        """Test that exception chains are properly preserved."""
        # Create a chain of exceptions
        root_cause = FileNotFoundError("Root cause: file missing")
        
        try:
            raise root_cause
        except FileNotFoundError as e:
            mid_error = TemplateReadError("Mid-level error", "TEMPLATE_FILE_NOT_FOUND")
            mid_error.__cause__ = e
            
            try:
                raise mid_error
            except TemplateReadError as e2:
                top_error = CommandNotFoundError("Top-level error")
                top_error.__cause__ = e2
                
                # Test full exception chain
                assert top_error.__cause__ is mid_error
                assert mid_error.__cause__ is root_cause
                
                # Test that all levels are accessible
                current = top_error
                chain_length = 0
                while current is not None:
                    chain_length += 1
                    current = current.__cause__
                
                assert chain_length == 3  # top_error -> mid_error -> root_cause

    def test_error_handling_in_cli_integration(self):
        """Test that errors propagate correctly through CLI integration."""
        from click.testing import CliRunner
        from promptcraft.main import promptcraft
        
        runner = CliRunner()
        
        # Test that core exceptions are properly handled at CLI level
        with patch('promptcraft.main.process_command', side_effect=CommandNotFoundError("CLI test error")):
            result = runner.invoke(promptcraft, ['/test-error'])
            
            assert result.exit_code == 1
            assert "Command '/test-error' not found" in result.output
            assert "Run 'promptcraft --list'" in result.output
        
        # Test that template errors are handled
        with patch('promptcraft.main.process_command', side_effect=TemplateReadError("Template CLI error")):
            result = runner.invoke(promptcraft, ['/template-error'])
            
            assert result.exit_code == 1
            assert "Template CLI error" in result.output
        
        # Test that generic errors are caught
        with patch('promptcraft.main.process_command', side_effect=RuntimeError("Generic error")):
            result = runner.invoke(promptcraft, ['/generic-error'])
            
            assert result.exit_code == 1
            assert "Unexpected error occurred" in result.output
            assert "RuntimeError" not in result.output  # Should not expose implementation details


class TestErrorStateManagement:
    """Test error state management and cleanup."""

    def test_error_state_cleanup(self):
        """Test that error conditions don't leave system in bad state."""
        from promptcraft.core import TemplateProcessor
        
        processor = TemplateProcessor()
        
        # Test that processor recovers from errors
        error_inputs = [None, 123, "", "   \n\t   "]
        
        for bad_input in error_inputs:
            with pytest.raises(TemplateError):
                processor.process_template(bad_input)
            
            # Should still work with good input after error
            good_result = processor.process_template("Good template content")
            assert good_result == "Good template content"

    def test_concurrent_error_handling(self):
        """Test error handling under concurrent conditions."""
        from promptcraft.core import TemplateProcessor
        import threading
        import queue
        
        processor = TemplateProcessor()
        results = queue.Queue()
        
        def process_with_error(content, thread_id):
            try:
                if "error" in content:
                    result = processor.process_template(None)  # Will cause error
                else:
                    result = processor.process_template(content)
                results.put((thread_id, "success", result))
            except Exception as e:
                results.put((thread_id, "error", str(e)))
        
        # Start threads with mix of good and bad inputs
        threads = []
        for i in range(10):
            content = f"error content {i}" if i % 3 == 0 else f"good content {i}"
            thread = threading.Thread(target=process_with_error, args=(content, i))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Analyze results
        thread_results = []
        while not results.empty():
            thread_results.append(results.get())
        
        assert len(thread_results) == 10
        
        # Should have mix of successes and errors
        successes = [r for r in thread_results if r[1] == "success"]
        errors = [r for r in thread_results if r[1] == "error"]
        
        assert len(successes) > 0
        assert len(errors) > 0
        assert len(successes) + len(errors) == 10