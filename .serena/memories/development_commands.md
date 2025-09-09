# PromptCraft Development Commands

## Installation Commands
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows)
venv\Scripts\activate

# Activate virtual environment (macOS/Linux)
source venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Install from source
pip install .
```

## Testing Commands
```bash
# Run all tests
pytest

# Run with coverage (95% target)
pytest --cov=promptcraft --cov-report=term-missing

# Run specific test markers
pytest -m "not slow"        # Skip slow tests
pytest -m integration       # Run integration tests only
pytest -m unit             # Run unit tests only
```

## CLI Execution
```bash
# Run installed CLI
promptcraft

# Run during development
python -m promptcraft.main

# Show help
promptcraft --help
```

## System Commands (Windows Focus)
- **List directory:** `dir` or `ls` (if available)
- **Change directory:** `cd`
- **Find files:** `where` or `find` (if available)  
- **Git operations:** `git status`, `git add`, `git commit`
- **Process management:** Task Manager or `tasklist`