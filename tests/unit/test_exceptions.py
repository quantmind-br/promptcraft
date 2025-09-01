"""Unit tests for exceptions module."""

import pytest
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