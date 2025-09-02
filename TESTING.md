# PromptCraft Testing Guide

This document provides comprehensive information about testing the PromptCraft CLI tool.

## Quick Start

```bash
# Install development dependencies
pip install -e .[dev]

# Run all tests with coverage
python run_tests.py

# Run tests without coverage (faster)
python run_tests.py --quick

# Run specific test categories
python run_tests.py --unit-only
python run_tests.py --integration
```

## Test Structure

```
tests/
├── __init__.py
└── unit/
    ├── test_core.py                    # Core functionality tests
    ├── test_main.py                    # CLI interface tests  
    ├── test_exceptions.py              # Exception handling tests
    ├── test_template_discovery.py      # Template discovery tests
    ├── test_cli_integration.py         # CLI integration tests
    ├── test_filesystem_interactions.py # File system tests
    ├── test_cross_platform_paths.py    # Cross-platform path tests
    └── test_clipboard_enhanced.py      # Enhanced clipboard tests
```

## Test Categories

### Unit Tests
- **Core Functions**: `test_core.py`
  - Template processing and argument substitution
  - Command path discovery and resolution
  - Template content generation
  - Command processing pipeline

- **CLI Interface**: `test_main.py`
  - Command-line argument parsing
  - Help and version display
  - Error message formatting
  - Exit code handling

- **Exception Handling**: `test_exceptions.py`
  - Custom exception classes
  - Error propagation through call stack
  - User-friendly error messages
  - Recovery mechanisms

### Integration Tests
- **CLI Integration**: `test_cli_integration.py`
  - End-to-end CLI command execution
  - Flag combinations and precedence
  - Output formatting consistency
  - Performance requirements (<150ms)

- **File System**: `test_filesystem_interactions.py`
  - Template file discovery
  - File reading and content processing
  - Error handling for missing/corrupted files
  - Temporary directory isolation

### Cross-Platform Tests
- **Path Handling**: `test_cross_platform_paths.py`
  - pathlib usage for cross-platform compatibility
  - File path resolution on different OS
  - Template directory scanning
  - Path normalization and edge cases

### Enhanced Feature Tests
- **Clipboard Functionality**: `test_clipboard_enhanced.py`
  - Clipboard mock scenarios
  - Error scenarios and fallback behavior
  - Integration with --stdout flag
  - Timeout and performance requirements

## Coverage Requirements

The test suite maintains **>95% code coverage** as measured by `coverage.py`.

### Coverage Configuration
- **Source**: `src/` directory
- **Branch Coverage**: Enabled
- **Exclusions**: Test files, cache directories
- **Reports**: Terminal, HTML, XML formats

### Coverage Commands
```bash
# Run tests with coverage (95% minimum)
pytest --cov=promptcraft --cov-fail-under=95

# Generate HTML report
pytest --cov=promptcraft --cov-report=html

# Generate XML report (for CI)
pytest --cov=promptcraft --cov-report=xml

# View coverage report
coverage report --show-missing
```

## Test Execution Options

### Using pytest directly
```bash
# Basic test run
pytest

# Verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_core.py

# Run specific test function
pytest tests/unit/test_core.py::test_template_processor_init

# Run tests with markers
pytest -m "not slow"

# Run with coverage
pytest --cov=promptcraft --cov-report=term-missing
```

### Using the test runner script
```bash
# Full test suite with coverage
python run_tests.py

# Quick run without coverage
python run_tests.py --quick

# Generate HTML coverage report
python run_tests.py --html

# Set custom coverage threshold
python run_tests.py --fail-under 90

# Run with specific markers
python run_tests.py --markers "not slow"

# Verbose output
python run_tests.py --verbose
```

## Test Markers

Tests are organized using pytest markers:

- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests  
- `@pytest.mark.slow`: Slow-running tests
- `@pytest.mark.clipboard`: Clipboard-related tests
- `@pytest.mark.filesystem`: File system tests
- `@pytest.mark.cross_platform`: Cross-platform tests

### Running specific markers
```bash
# Run only unit tests
pytest -m unit

# Skip slow tests
pytest -m "not slow"

# Run clipboard tests only
pytest -m clipboard

# Combine markers
pytest -m "unit and not slow"
```

## Continuous Integration

### GitHub Actions
The project uses GitHub Actions for automated testing:

- **Matrix Testing**: Python 3.10, 3.11, 3.12 on Ubuntu, Windows, macOS
- **Coverage Reporting**: Uploads to Codecov
- **Coverage Badge**: Auto-generated and updated
- **PR Comments**: Coverage reports posted on pull requests

### Coverage Reports
- **Codecov**: https://codecov.io/gh/promptcraft/promptcraft
- **GitHub Pages**: Coverage HTML reports deployed automatically
- **PR Integration**: Coverage changes reported on pull requests

## Performance Requirements

### CLI Performance
- **Target**: <150ms for all CLI operations
- **Measurement**: Included in performance tests
- **Monitoring**: Tracked in CI/CD pipeline

### Test Performance
- **Fast Tests**: Unit tests should run in <5 seconds total
- **Full Suite**: Complete test suite should run in <30 seconds
- **Coverage**: Coverage generation adds ~10-20% overhead

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Install in development mode
   pip install -e .[dev]
   ```

2. **Permission Errors (Unix/Linux)**
   ```bash
   # Some tests may skip on permission issues
   # This is expected behavior for cross-platform compatibility
   ```

3. **Clipboard Tests on Headless Systems**
   ```bash
   # Clipboard tests automatically detect headless environments
   # Set PROMPTCRAFT_NO_CLIPBOARD=true to force headless mode
   export PROMPTCRAFT_NO_CLIPBOARD=true
   ```

4. **Coverage Below Threshold**
   ```bash
   # Check which lines are missing coverage
   coverage report --show-missing
   
   # Generate detailed HTML report
   coverage html
   # Open htmlcov/index.html in browser
   ```

### Test Environment Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install project and dependencies
pip install -e .[dev]

# Verify installation
python -c "import promptcraft; print('Installation successful')"

# Run test suite
python run_tests.py
```

### Debug Mode

```bash
# Run tests with Python debug mode
python -X dev run_tests.py

# Run specific failing test with verbose output
pytest -xvs tests/unit/test_core.py::test_failing_function

# Drop into debugger on failure
pytest --pdb tests/unit/test_core.py::test_failing_function
```

## Writing New Tests

### Test Structure
```python
"""Module docstring describing test purpose."""

import pytest
from unittest.mock import patch, Mock
from click.testing import CliRunner

from promptcraft.core import function_to_test
from promptcraft.exceptions import ExpectedException


class TestFunctionality:
    """Test class for related functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_basic_functionality(self):
        """Test basic functionality with descriptive docstring."""
        # Arrange
        input_data = "test input"
        expected = "expected output"
        
        # Act
        result = function_to_test(input_data)
        
        # Assert
        assert result == expected
    
    @patch('promptcraft.core.external_dependency')
    def test_with_mocking(self, mock_dependency):
        """Test functionality with mocked dependencies."""
        # Configure mock
        mock_dependency.return_value = "mocked value"
        
        # Test with mock
        result = function_to_test("input")
        
        # Verify mock was called
        mock_dependency.assert_called_once_with("input")
        assert result == "expected with mock"
```

### Test Guidelines
1. **Descriptive Names**: Test names should clearly describe what is being tested
2. **Arrange-Act-Assert**: Structure tests with clear sections
3. **One Concept**: Each test should verify one specific behavior
4. **Independent**: Tests should not depend on each other
5. **Deterministic**: Tests should produce consistent results
6. **Fast**: Unit tests should complete quickly
7. **Isolated**: Use mocks for external dependencies

### Coverage Guidelines
1. **Positive Cases**: Test normal operation paths
2. **Negative Cases**: Test error conditions and edge cases
3. **Boundary Conditions**: Test limits and edge values
4. **Integration**: Test component interactions
5. **Platform-Specific**: Test platform-specific behavior
6. **Performance**: Include performance verification where relevant

## Maintenance

### Regular Tasks
- **Coverage Review**: Monthly review of coverage reports
- **Performance Monitoring**: Track test execution times
- **Test Cleanup**: Remove obsolete tests, update outdated mocks
- **Documentation Updates**: Keep testing documentation current

### Test Metrics
- **Total Tests**: Current count and growth over time
- **Coverage Percentage**: Maintain >95% coverage
- **Execution Time**: Monitor for performance regressions
- **Failure Rate**: Track test stability and flakiness

For more information, see the main project documentation and individual test file docstrings.