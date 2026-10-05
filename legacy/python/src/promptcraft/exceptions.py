"""Custom exceptions for the PromptCraft CLI tool."""


class PromptCraftError(Exception):
    """Base exception class for PromptCraft errors."""
    pass


class TemplateError(PromptCraftError):
    """Exception raised for template processing errors."""
    pass


class ConfigurationError(PromptCraftError):
    """Exception raised for configuration-related errors."""
    pass


class CommandNotFoundError(PromptCraftError):
    """Exception raised when a command template cannot be found.

    This exception is raised when the system cannot locate a command template
    file in any of the configured search paths. It typically occurs when:
    - A user requests a command that doesn't exist
    - Template files have been moved or deleted
    - Search paths are misconfigured

    Attributes:
        message (str): Human-readable error message
        error_code (str): Structured error code for programmatic handling

    Example:
        >>> raise CommandNotFoundError("Command 'invalid-cmd' not found")
    """

    def __init__(self, message: str, error_code: str = "COMMAND_NOT_FOUND"):
        """Initialize CommandNotFoundError.

        Args:
            message: Human-readable error message
            error_code: Structured error code for programmatic handling
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class TemplateReadError(PromptCraftError):
    """Exception raised when template file reading fails.

    This exception is raised when the system encounters I/O issues while
    reading template content. It typically occurs when:
    - Template files have permission restrictions
    - Files are corrupted or contain invalid content
    - Disk I/O errors occur during file access
    - Files are locked by other processes

    Attributes:
        message (str): Human-readable error message
        error_code (str): Structured error code for programmatic handling

    Example:
        >>> raise TemplateReadError("Failed to read: Permission denied")
    """

    def __init__(self, message: str, error_code: str = "TEMPLATE_READ_ERROR"):
        """Initialize TemplateReadError.

        Args:
            message: Human-readable error message
            error_code: Structured error code for programmatic handling
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
