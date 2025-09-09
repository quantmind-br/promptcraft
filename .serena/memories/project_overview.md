# PromptCraft Project Overview

## Project Purpose
PromptCraft CLI is a command-line tool for managing prompt templates efficiently. It helps developers and content creators manage, organize, and utilize prompt templates effectively.

## Technology Stack
- **Python:** 3.10+ (setuptools build system)
- **CLI Framework:** Click 8.0+
- **Clipboard Operations:** pyperclip 1.8+
- **Testing:** Pytest 7+ with pytest-cov, pytest-benchmark
- **Build System:** setuptools>=61.0 with wheel support
- **Package Management:** pip with pyproject.toml support

## Project Structure
```
promptcraft/
├── src/promptcraft/          # Main package source
│   ├── main.py              # CLI entry point
│   ├── core.py              # Core template processing
│   ├── exceptions.py        # Custom exceptions
│   └── __init__.py         # Package init
├── tests/                   # Test files with 95% coverage target
├── docs/                   # Documentation and stories
├── .bmad-core/            # Agent configuration
└── pyproject.toml         # Project configuration
```

## Key Features
- Template management and organization
- Command-line interface for workflow integration
- Clipboard operations for quick template access
- Extensible architecture for custom template processing
- Cross-platform support (Windows, macOS, Linux)