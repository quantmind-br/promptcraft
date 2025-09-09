# PromptCraft Code Style and Conventions

## Python Code Standards
- **Python Version:** 3.10+ minimum
- **Type Hints:** Strongly encouraged (based on project structure)
- **Docstrings:** Use for public APIs and complex functions
- **Import Organization:** Standard Python conventions
- **Exception Handling:** Custom exceptions in `exceptions.py`

## Testing Standards
- **Framework:** Pytest 7+
- **Coverage Target:** 95% minimum (enforced in CI)
- **Test Organization:**
  - Unit tests: `tests/unit/`
  - Integration tests: marked with `@pytest.mark.integration`
  - Performance tests: marked with `@pytest.mark.benchmark`
- **Test Naming:**
  - Files: `test_*.py` or `*_test.py`
  - Classes: `Test*`
  - Functions: `test_*`

## Project Structure Conventions
- **Source Layout:** `src/` layout with `src/promptcraft/`
- **Entry Point:** `main.py` for CLI execution
- **Core Logic:** `core.py` for template processing
- **Error Handling:** Centralized in `exceptions.py`

## Build and Package Standards
- **Configuration:** All in `pyproject.toml` (single source)
- **Version Management:** pyproject.toml only
- **Dependencies:** Runtime in `dependencies`, dev in `optional-dependencies.dev`
- **Console Scripts:** Defined in `[project.scripts]`

## Quality Gates
- All tests must pass with 95% coverage
- Code must be installable via `pip install .`
- Console script `promptcraft` must work after installation
- Cross-platform compatibility required