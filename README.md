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

### Prerequisites

- Python 3.10 or higher
- pip (Python package installer)

### Install from Source

1. Clone the repository:
   ```bash
   git clone https://github.com/promptcraft/promptcraft.git
   cd promptcraft
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install the package in development mode:
   ```bash
   pip install -e .
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

## Usage

```bash
promptcraft --help
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions and support, please open an issue on GitHub.