---
title: Contributing
description: How to contribute to Vantage CLI development
---

Short guide for working on Vantage CLI.

## Environment Setup

```bash
git clone https://github.com/vantagecompute/vantage-cli.git
cd vantage-cli
pip install uv
uv sync
```

Run tests:

```bash
just unit
```

## Project Structure (CLI)

```text
vantage_cli/
    main.py        # Entry (Typer)
    auth.py        # Auth + persona
    cache.py       # Token cache helpers
    client.py      # HTTP helpers
    gql_client.py  # GraphQL client factory
    config.py      # Settings + profiles
    constants.py   # Paths & consts
    exceptions.py  # Error hierarchy
    schemas.py     # Pydantic models
    format.py      # Output formatting
```

## Adding a Command

```python
import typer
from vantage_cli.config import attach_settings

app = typer.Typer()

@app.command()
@attach_settings
async def ping(ctx: typer.Context):
        """Simple connectivity check."""
        typer.echo(ctx.obj.settings.api_base_url)
```

Register the sub-app in `main.py`.

## Standards

- Python 3.12+
- Type hints required
- `--json` for structured output where useful
- Minimal side effects in library functions

## Testing

```bash
just lint

just typecheck

just unit

just integration
```

Write focused tests for each new command (happy + error path).

## Logging & Errors

- Use `Abort` (if provided) for user-facing failures
- Add `-v` to surface debug logs when diagnosing
- Avoid leaking tokens or raw tracebacks

## Submitting Changes

1. Branch
2. Update / add tests
3. Lint & type check (if configured)
4. Write concise PR description

## Release (Internal)

- Bump version (pyproject.toml)
- Update CHANGELOG
- Tag & publish

## Communication

Open issues with steps, expected vs actual, environment info.

---
Thanks for contributing.
