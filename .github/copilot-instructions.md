# GitHub Copilot Instructions for Vantage CLI

## Python Command Execution

**ALWAYS use `uv run` for Python commands in this project.**

This project uses `uv` for dependency management and virtual environment handling. All Python commands must be prefixed with `uv run`.

### Examples:

✅ **CORRECT:**
- `uv run python script.py`


❌ **INCORRECT:**
- `python script.py`
- `pytest tests/`
- `python -m vantage_cli.main`
- `vantage --help`
- `coverage run`
- `mypy .`
- `black .`
- `ruff check`

### Just Commands (Primary Development Workflow):

**Testing:**
- `just unit` - Run unit tests with coverage (80% threshold)
- `just integration` - Run integration tests  
- `just coverage-all` - Run full test suite with combined coverage

**Code Quality:**
- `just typecheck` - Run static type checker (pyright)
- `just lint` - Check code against style standards (codespell + ruff)
- `just fmt` - Apply coding style standards (ruff format + fix)

**Documentation:**
- `just docs-dev` - Start Docusaurus development server
- `just docs-dev-port [port]` - Start dev server on specific port
- `just docs-build` - Build documentation for production
- `just docs-serve` - Serve built documentation
- `just docs-clean` - Clean documentation build artifacts
- `just docs-help` - Show documentation commands

**Development:**
- `just lock` - Regenerate uv.lock file

### Direct UV Commands (When Needed):
- Run CLI: `uv run vantage [command]`
- Specific test: `uv run pytest tests/unit/test_example.py::test_function`
- Add dependency: `uv add package-name`
- Add dev dependency: `uv add --dev package-name`

### Installation Commands:
- Install dependencies: `uv sync`
- Add new dependency: `uv add package-name`
- Add dev dependency: `uv add --dev package-name`
- Regenerate lock: `just lock`

## Project Structure

This is a Python CLI application using:
- `uv` for dependency management
- `typer` for CLI framework
- `rich` for terminal output
- `pytest` for testing
- `RenderStepOutput` for progress rendering with JSON bypass support

## Test Patterns

When working with tests, ensure:
1. MockConsole includes all necessary Rich console methods
2. Use `RenderStepOutput.json_bypass()` for JSON output tests
3. All async functions are properly awaited in tests
4. Function signatures match current implementation

## Never Forget

**EVERY Python command MUST start with `uv run`** - this is critical for proper dependency resolution and virtual environment isolation in this project.