# PromptCraft CLI

A command-line tool for managing prompt templates efficiently.

## Description

PromptCraft CLI is a powerful command-line interface tool designed to help developers and content creators manage, organize, and utilize prompt templates effectively. Whether you're working with AI models, documentation templates, or any form of structured content, PromptCraft streamlines your workflow.

## Features

- Template management and organization
- Command-line interface for efficient workflow integration
- Clipboard operations for quick template access
- Extensible architecture for custom template processing

## Installation

### System Requirements

- **Python:** 3.10 or higher
- **Operating Systems:** Windows, macOS, Linux
- **pip:** Python package installer (usually comes with Python)

### Quick Installation

For end users, install PromptCraft directly from source:

```bash
# Clone the repository
git clone https://github.com/promptcraft/promptcraft.git
cd promptcraft

# Install the package
pip install .
```

### Virtual Environment Installation (Recommended)

Using a virtual environment prevents dependency conflicts:

```bash
# Create a virtual environment
python -m venv promptcraft-env

# Activate the virtual environment
# On Windows:
promptcraft-env\Scripts\activate
# On macOS/Linux:
source promptcraft-env/bin/activate

# Clone and install
git clone https://github.com/promptcraft/promptcraft.git
cd promptcraft
pip install .
```

### Development Installation

For developers who want to contribute or modify the code:

```bash
# Clone the repository
git clone https://github.com/promptcraft/promptcraft.git
cd promptcraft

# Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install in editable mode with development dependencies
pip install -e ".[dev]"
```

### Verifying Installation

After installation, verify that PromptCraft is working correctly:

```bash
# Check version
promptcraft --version

# View help
promptcraft --help

# Initialize a project to test functionality
promptcraft --init
```

### Troubleshooting Installation

#### Common Issues

**Permission Errors on Windows:**
```bash
# Run as administrator or use user installation
pip install --user .
```

**Permission Errors on macOS/Linux:**
```bash
# Don't use sudo, use virtual environment instead
python -m venv venv
source venv/bin/activate
pip install .
```

**Python Not Found:**
- Ensure Python 3.10+ is installed and in your PATH
- Try `python3` instead of `python` on macOS/Linux
- On Windows, try `py` instead of `python`

**pip Not Found:**
```bash
# Install pip if missing
python -m ensurepip --upgrade
```

#### Clean Installation

If you encounter issues, try a clean installation:

```bash
# Uninstall existing installation
pip uninstall promptcraft

# Clear pip cache
pip cache purge

# Reinstall
pip install .
```

## Development Setup

### Setting up Development Environment

1. Clone the repository and navigate to the project directory
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

### Project Structure

```
promptcraft/
├── src/
│   └── promptcraft/
│       ├── __init__.py
│       ├── main.py          # CLI entry point
│       ├── core.py          # Core template processing
│       └── exceptions.py    # Custom exceptions
├── tests/                   # Test files (to be created)
├── pyproject.toml          # Project configuration
├── README.md              # This file
└── .gitignore            # Git ignore rules
```

### Running Tests

```bash
pytest
```

### Running the CLI

After installation, you can run the CLI with:

```bash
promptcraft
```

Or during development:

```bash
python -m promptcraft.main
```

## Complete Command Reference

PromptCraft provides a comprehensive command-line interface for managing prompt templates. All commands follow consistent patterns for predictable usage.

### Core Syntax

```bash
promptcraft [COMMAND] [ARGUMENTS...] [FLAGS]
```

### Primary Commands

#### Template Execution
Execute any template command with optional arguments:

```bash
# Basic template execution (copies to clipboard by default)
promptcraft my-template

# Execute with single argument
promptcraft create-story "User Authentication"

# Execute with multiple arguments
promptcraft fix-bug "critical" "security vulnerability" "auth module"

# Commands work with or without leading slash
promptcraft /create-story "User Story"
promptcraft create-story "User Story"

# Arguments with spaces must be quoted
promptcraft generate-code "class UserManager" "authentication logic"
```

#### Project Initialization
Set up PromptCraft structure in current directory:

```bash
# Initialize project with example templates
promptcraft --init

# After initialization, your project will have:
# .promptcraft/commands/exemplo.md - Example template
```

#### Template Discovery
List all available templates from discovery paths:

```bash
# List all discovered templates
promptcraft --list

# Output shows template name and description
# Templates are loaded from:
#   - .promptcraft/commands/ (current directory)
#   - ~/.promptcraft/commands/ (user home directory)
```

#### Version Information
Display current PromptCraft version:

```bash
# Show version information
promptcraft --version
```

#### Help and Documentation
Access built-in help system:

```bash
# Show complete help with all options
promptcraft --help

# Help includes usage patterns and examples
```

### Command Flags and Options

#### Output Control Flags

**`--stdout`** - Output to terminal instead of clipboard
```bash
# Default behavior: copy to clipboard
promptcraft create-story "Feature Request"

# Terminal output: display result in console
promptcraft create-story "Feature Request" --stdout

# Useful for debugging or headless environments
promptcraft debug-template "test data" --stdout
```

#### Operational Flags

**`--init`** - Initialize project structure
```bash
# Create .promptcraft/commands/ directory with examples
promptcraft --init

# Safe to run multiple times (won't overwrite existing templates)
```

**`--list`** - Display all available templates
```bash
# Show template name and first line (description)
promptcraft --list

# Example output:
# Available commands:
# exemplo - Template example for PromptCraft demonstration
# create-story - Generate user story template
```

**`--version`** - Show version information
```bash
# Display current version
promptcraft --version

# Example output: PromptCraft CLI version 1.0.0
```

**`--help`** - Display help information
```bash
# Show complete usage information
promptcraft --help
```

### Command Execution Patterns

#### Individual Developer Workflow
```bash
# Morning routine: check available templates
promptcraft --list

# Create user story for new feature
promptcraft create-story "Payment Integration" "stripe checkout"

# Generate code review checklist
promptcraft code-review "payment-service.py"

# Create bug report template
promptcraft bug-report "critical" "payment processing failure"
```

#### Team Collaboration Scenarios
```bash
# Project initialization for new team member
promptcraft --init

# Standardized story creation
promptcraft epic-story "User Management" "authentication authorization"

# Code documentation generation
promptcraft api-docs "UserController" "REST endpoints"

# Meeting notes template
promptcraft meeting-notes "Sprint Planning" "2024-01-15"
```

#### Development Integration Patterns
```bash
# Git commit message generation
promptcraft commit-msg "feat" "add user authentication"

# Pull request description
promptcraft pr-description "authentication-feature" "user login system"

# Documentation updates
promptcraft update-docs "authentication" "login flow changes"
```

#### Advanced Usage Scenarios
```bash
# Complex multi-argument templates
promptcraft api-spec "UserService" "POST /users" "create user endpoint"

# Template with environment-specific content
promptcraft deploy-notes "production" "v2.1.0" "authentication updates"

# Debug and development templates
promptcraft debug-session "authentication-bug" --stdout
```

### Template Discovery and Organization

#### Discovery Paths
PromptCraft automatically searches for templates in these locations (in order):

1. **Project-level templates**: `.promptcraft/commands/`
   - Templates specific to current project
   - Shared with team via version control
   - Takes precedence over user templates

2. **User-level templates**: `~/.promptcraft/commands/`
   - Personal templates across all projects
   - User-specific customizations
   - Backup location for common templates

#### Template File Requirements
- **File Extension**: Must be `.md` (Markdown)
- **File Name**: Becomes the command name (without .md extension)
- **First Line**: Used as template description in `--list` output
- **Content**: Template body with `$ARGUMENTS` placeholders

#### Template Naming Conventions
```bash
# Good template names (recommended):
create-story.md          → promptcraft create-story
bug-report.md           → promptcraft bug-report
api-documentation.md    → promptcraft api-documentation
meeting-notes.md        → promptcraft meeting-notes

# Valid but not recommended:
CreateStory.md          → promptcraft CreateStory
bug_report.md           → promptcraft bug_report
api.docs.md            → promptcraft api.docs
```

### Error Handling and Troubleshooting

#### Common Command Errors

**Command Not Found**
```bash
# Error example:
promptcraft nonexistent-command
# Output: Command '/nonexistent-command' not found
#         Run 'promptcraft --list' to see available commands

# Resolution: Check available commands
promptcraft --list
```

**Template Read Errors**
```bash
# When template file is corrupted or inaccessible:
# Output: Unable to read template file: /path/to/template.md

# Resolution: Verify file permissions and content
ls -la .promptcraft/commands/
```

**Clipboard Access Issues**
```bash
# When clipboard is unavailable:
promptcraft my-template
# Output: Clipboard unavailable, use --stdout instead
#         [Template content displayed in terminal]

# Resolution: Use --stdout flag
promptcraft my-template --stdout
```

#### Platform-Specific Considerations

**Windows**
```bash
# Use quotes for arguments with spaces
promptcraft create-story "Feature Name"

# PowerShell compatibility
promptcraft create-story 'Feature Name'
```

**macOS/Linux**
```bash
# Single or double quotes both work
promptcraft create-story "Feature Name"
promptcraft create-story 'Feature Name'

# Shell expansion considerations
promptcraft create-story "Feature $(date)"
```

#### Debugging Commands
```bash
# Verify installation
promptcraft --version

# Check template discovery
promptcraft --list

# Test template execution with terminal output
promptcraft your-template --stdout

# Check project structure
ls -la .promptcraft/commands/
```

### Integration with Development Tools

#### Git Integration
```bash
# Git hook integration example
promptcraft commit-msg "$(git diff --name-only --cached)"

# Pre-commit template generation
promptcraft pre-commit-checklist --stdout
```

#### IDE Integration
```bash
# VS Code task integration
promptcraft code-review "${file}" --stdout

# Documentation generation
promptcraft class-docs "${className}" --stdout
```

#### CI/CD Integration
```bash
# Deployment documentation
promptcraft deploy-notes "${CI_COMMIT_TAG}" "${ENVIRONMENT}"

# Release notes generation
promptcraft release-notes "${VERSION}" --stdout
```

## Template Creation Guide

### Template File Format

PromptCraft templates are Markdown files with a specific structure:

```markdown
# First line: Template description (shows in --list)
Generate a user story template

# Template body with placeholders
## User Story: $ARGUMENTS[0]

**As a** user,
**I want** $ARGUMENTS[1],
**so that** $ARGUMENTS[2].

### Acceptance Criteria
- [ ] $ARGUMENTS[3]
- [ ] Comprehensive testing completed
- [ ] Documentation updated
```

### Placeholder System

**Basic Placeholders**
- `$ARGUMENTS[0]` - First argument
- `$ARGUMENTS[1]` - Second argument
- `$ARGUMENTS[n]` - Nth argument (0-indexed)

**Advanced Usage**
```markdown
# Multiple placeholder usage
## $ARGUMENTS[0] Implementation

**Priority**: $ARGUMENTS[1]
**Component**: $ARGUMENTS[2]
**Description**: $ARGUMENTS[3]

### Implementation Notes
- Focus on $ARGUMENTS[0] functionality
- Consider $ARGUMENTS[1] priority level
- Integrate with $ARGUMENTS[2] component
```

### Template Examples

#### Simple Template: `hello.md`
```markdown
Simple greeting template
Hello $ARGUMENTS[0]! Welcome to PromptCraft.
```

Usage: `promptcraft hello "World"`
Output: `Hello World! Welcome to PromptCraft.`

#### Complex Template: `user-story.md`
```markdown
Generate comprehensive user story with acceptance criteria
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
- Estimated effort: TBD

### Definition of Done
- [ ] Implementation complete
- [ ] Tests written and passing
- [ ] Code reviewed
- [ ] Documentation updated
```

Usage: `promptcraft user-story "Authentication" "developer" "secure login system" "users can access protected resources" "Login form validates credentials"`

#### Team Template: `sprint-planning.md`
```markdown
Sprint planning meeting template
# Sprint Planning - $ARGUMENTS[0]

**Sprint Goal**: $ARGUMENTS[1]
**Duration**: $ARGUMENTS[2]
**Team**: $ARGUMENTS[3]

## Sprint Backlog
### Priority Items
1. $ARGUMENTS[4]

### Additional Items
- TBD during planning

## Capacity Planning
- Total capacity: TBD
- Planned velocity: TBD

## Risk Assessment
- Risk: $ARGUMENTS[5]
- Mitigation: TBD
```

### Template Best Practices

#### Naming Conventions
- Use lowercase with hyphens: `user-story.md`, `api-docs.md`
- Be descriptive: `bug-report.md` instead of `bug.md`
- Group related templates: `git-commit.md`, `git-pr.md`

#### Content Guidelines
- First line is description (clear and concise)
- Use meaningful placeholder names in comments
- Include examples in template body
- Structure content logically
- Consider team consistency

#### Organization Strategies
```bash
# By category
.promptcraft/commands/
├── stories/
│   ├── user-story.md
│   └── epic-story.md
├── development/
│   ├── code-review.md
│   └── bug-report.md
└── documentation/
    ├── api-docs.md
    └── readme-update.md
```

## Troubleshooting

### Common Issues and Solutions

#### Clipboard Integration Issues

**Issue**: Clipboard operations fail on headless systems
```bash
# Symptom:
promptcraft my-template
# Output: Clipboard unavailable, use --stdout instead

# Solution 1: Use --stdout flag
promptcraft my-template --stdout

# Solution 2: Set up X11 forwarding (Linux/macOS remote)
ssh -X user@remote-host
export DISPLAY=:0
promptcraft my-template
```

**Issue**: Clipboard access denied on Linux
```bash
# Symptom: Permission denied accessing clipboard

# Solution: Install required clipboard utilities
# Ubuntu/Debian:
sudo apt-get install xclip xsel

# Fedora/RHEL:
sudo dnf install xclip xsel

# Arch Linux:
sudo pacman -S xclip xsel
```

**Issue**: Clipboard not working in WSL (Windows Subsystem for Linux)
```bash
# Solution 1: Install wslu package
sudo apt update && sudo apt install wslu

# Solution 2: Use --stdout flag as fallback
promptcraft my-template --stdout
```

#### Platform-Specific Issues

**Windows PowerShell Issues**
```powershell
# Issue: Command not recognized
promptcraft --version
# Error: 'promptcraft' is not recognized

# Solution 1: Restart PowerShell after installation
# Solution 2: Check PATH environment variable
$env:PATH -split ';' | Select-String python

# Solution 3: Use Python module directly
python -m promptcraft.main --version
```

**macOS Permission Issues**
```bash
# Issue: Permission denied on template directory creation
promptcraft --init
# Error: Permission denied: ~/.promptcraft/commands/

# Solution: Fix directory permissions
chmod 755 ~
mkdir -p ~/.promptcraft/commands
chmod 755 ~/.promptcraft ~/.promptcraft/commands
```

**Linux Distribution-Specific Issues**
```bash
# Issue: Python 3.10+ not available
# Solution varies by distribution:

# Ubuntu 20.04 (add deadsnakes PPA):
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.11 python3.11-pip

# CentOS/RHEL 8 (enable PowerTools):
sudo dnf config-manager --enable powertools
sudo dnf install python39

# Use specific Python version:
python3.11 -m pip install .
```

#### Installation and Dependency Issues

**Issue**: pip installation fails with permission errors
```bash
# Symptom:
pip install .
# Error: ERROR: Could not install packages due to an EnvironmentError

# Solution 1: Use virtual environment (recommended)
python -m venv promptcraft-env
source promptcraft-env/bin/activate  # Linux/macOS
promptcraft-env\Scripts\activate     # Windows
pip install .

# Solution 2: User installation (not recommended for development)
pip install --user .
```

**Issue**: Dependencies conflict with existing packages
```bash
# Symptom: Package conflicts during installation

# Solution: Use isolated virtual environment
python -m venv --clear promptcraft-clean-env
source promptcraft-clean-env/bin/activate
pip install --upgrade pip
pip install .
```

**Issue**: Template discovery not working
```bash
# Symptom:
promptcraft --list
# Output: No commands found

# Diagnostic steps:
# 1. Check if directories exist
ls -la .promptcraft/commands/
ls -la ~/.promptcraft/commands/

# 2. Verify template file format
cat .promptcraft/commands/exemplo.md

# 3. Check file permissions
ls -la .promptcraft/commands/*.md

# Solutions:
# Re-initialize project
promptcraft --init

# Manually create template
mkdir -p .promptcraft/commands
echo -e "Example template\nHello $ARGUMENTS[0]!" > .promptcraft/commands/hello.md
```

#### Development and Testing Issues

**Issue**: Tests failing after installation
```bash
# Run diagnostic tests
python -m pytest tests/ -v

# Common fixes:
# 1. Install development dependencies
pip install -e ".[dev]"

# 2. Update test database
python -m pytest --co -q  # Check test discovery

# 3. Clear Python cache
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +
```

**Issue**: Import errors in development
```bash
# Symptom:
python -m promptcraft.main
# Error: ModuleNotFoundError: No module named 'promptcraft'

# Solution: Install in editable mode
pip install -e .

# Or use Python path directly
PYTHONPATH=src python -m promptcraft.main
```

#### Performance Issues

**Issue**: Slow template discovery on large directories
```bash
# Symptom: `promptcraft --list` takes a long time

# Diagnostic: Check directory size
find .promptcraft/commands/ -name "*.md" | wc -l
find ~/.promptcraft/commands/ -name "*.md" | wc -l

# Solution: Organize templates in subdirectories
# Move infrequently used templates to archive/
mkdir -p .promptcraft/commands/archive/
mv .promptcraft/commands/old-*.md .promptcraft/commands/archive/
```

### Getting Help

#### Debug Information Collection
When reporting issues, include this diagnostic information:

```bash
# System information
promptcraft --version
python --version
pip --version
uname -a  # Linux/macOS
systeminfo | findstr /B /C:"OS Name" /C:"OS Version"  # Windows

# PromptCraft configuration
promptcraft --list
ls -la .promptcraft/commands/ 2>/dev/null || echo "No local templates"
ls -la ~/.promptcraft/commands/ 2>/dev/null || echo "No user templates"

# Test basic functionality
promptcraft --help
echo "Test template" | promptcraft test-template --stdout
```

#### Community Support
- **GitHub Issues**: Report bugs and feature requests
- **Discussions**: Ask questions and share templates
- **Wiki**: Community-contributed examples and guides

## Contributing Guidelines

### Development Environment Setup

#### Prerequisites
- **Python 3.10+** installed and available in PATH
- **Git** for version control
- **Virtual environment** tools (venv recommended)
- **Text editor** or IDE (VS Code, PyCharm, etc.)

#### Initial Setup
```bash
# 1. Fork the repository on GitHub
# 2. Clone your fork locally
git clone https://github.com/YOUR_USERNAME/promptcraft.git
cd promptcraft

# 3. Create development environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# 4. Install in development mode
pip install -e ".[dev]"

# 5. Verify installation
promptcraft --version
pytest tests/ -v
```

#### Development Workflow
```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make your changes
# ... edit code ...

# Run tests frequently
pytest tests/ -v

# Check code formatting
black src/ tests/
flake8 src/ tests/

# Run complete test suite
pytest tests/ --cov=promptcraft --cov-report=html

# Commit your changes
git add .
git commit -m "feat: add your feature description"

# Push and create pull request
git push origin feature/your-feature-name
```

### Code Contribution Standards

#### Code Style
- **Formatting**: Use `black` for code formatting
- **Linting**: Use `flake8` for code linting  
- **Type Hints**: Include type annotations for all functions
- **Docstrings**: Follow Google-style docstring format
- **Line Length**: Maximum 88 characters (black default)

#### Example Code Style
```python
def process_template(template_path: str, arguments: List[str]) -> str:
    """Process template file with provided arguments.
    
    Args:
        template_path: Path to the template file
        arguments: List of arguments to substitute
        
    Returns:
        Processed template content with arguments substituted
        
    Raises:
        TemplateReadError: When template file cannot be read
        ArgumentError: When required arguments are missing
    """
    # Implementation here
    pass
```

#### Testing Requirements

**Test Coverage**: Minimum 95% code coverage required

```bash
# Run tests with coverage
pytest tests/ --cov=promptcraft --cov-report=term-missing

# Generate HTML coverage report
pytest tests/ --cov=promptcraft --cov-report=html
open htmlcov/index.html  # View detailed coverage
```

**Test Types Required**:
1. **Unit Tests**: Test individual functions and classes
2. **Integration Tests**: Test CLI commands end-to-end
3. **Template Tests**: Validate template processing logic
4. **Error Handling Tests**: Test exception scenarios

**Test Organization**:
```
tests/
├── unit/
│   ├── test_core.py          # Core functionality tests
│   ├── test_main.py          # CLI interface tests
│   └── test_exceptions.py    # Exception handling tests
├── integration/
│   └── test_cli_integration.py  # End-to-end CLI tests
└── fixtures/
    └── templates/            # Test template files
```

#### Commit Message Standards

Use conventional commit format:
```bash
# Format: type(scope): description
feat(cli): add --debug flag for verbose output
fix(core): handle empty template files gracefully  
docs(readme): update installation instructions
test(cli): add integration tests for --init command
refactor(core): extract template parsing logic
```

**Commit Types**:
- `feat`: New features
- `fix`: Bug fixes
- `docs`: Documentation changes
- `test`: Test additions or modifications
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `chore`: Maintenance tasks

### Pull Request Guidelines

#### Before Submitting
- [ ] All tests pass locally
- [ ] Code coverage ≥ 95%
- [ ] Code formatted with `black`
- [ ] No linting errors (`flake8`)
- [ ] Documentation updated if needed
- [ ] Commit messages follow conventional format

#### Pull Request Template
```markdown
## Description
Brief description of changes made

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)  
- [ ] Breaking change (fix or feature causing existing functionality to change)
- [ ] Documentation update

## Testing
- [ ] New tests added for new functionality
- [ ] All existing tests pass
- [ ] Manual testing completed

## Screenshots (if applicable)
Add screenshots to help explain your changes

## Checklist
- [ ] My code follows the project's style guidelines
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] New and existing unit tests pass locally
```

#### Review Process
1. **Automated Checks**: CI/CD pipeline runs tests and linting
2. **Code Review**: At least one maintainer reviews code
3. **Discussion**: Address feedback and questions
4. **Approval**: Maintainer approves after all checks pass
5. **Merge**: Squash and merge to main branch

### Documentation Contributions

#### Documentation Types
- **Code Documentation**: Docstrings and inline comments
- **User Documentation**: README, usage guides, examples
- **Developer Documentation**: Contributing guidelines, architecture docs
- **API Documentation**: Generated from docstrings

#### Documentation Standards
- **Clarity**: Write for the target audience (user vs developer)
- **Completeness**: Cover all features and edge cases
- **Examples**: Include practical, working examples
- **Maintenance**: Keep documentation in sync with code changes

### Release Process

#### Versioning
- Follow [Semantic Versioning](https://semver.org/) (MAJOR.MINOR.PATCH)
- Update version in `pyproject.toml`
- Create git tag for releases

#### Release Checklist
- [ ] All tests passing on main branch
- [ ] Version number updated
- [ ] CHANGELOG.md updated
- [ ] Documentation reviewed and updated
- [ ] Release notes prepared
- [ ] Git tag created
- [ ] Package built and tested
- [ ] Release published

### Community Guidelines

#### Code of Conduct
- Be respectful and inclusive in all interactions
- Focus on constructive feedback and solutions
- Help newcomers get started with contributing
- Follow project communication guidelines

#### Getting Support
- **Questions**: Use GitHub Discussions
- **Bugs**: Create GitHub Issues with reproduction steps
- **Features**: Discuss in GitHub Issues before implementing
- **Urgent Issues**: Tag maintainers in issues

Thank you for contributing to PromptCraft! 🚀

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions and support, please open an issue on GitHub.