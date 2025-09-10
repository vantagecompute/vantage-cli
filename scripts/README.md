# Scripts Directory

This directory contains utility scripts for the Vantage CLI project.

## update_docs_version.py

**Purpose**: Automatically updates documentation files with the current version from `pyproject.toml`.

**Files Updated**:
- `docs/_data/project.yml` - Updates version and date fields
- `docs/_config.yml` - Adds/updates version field
- `docs/index.md` - Adds version to front matter

**Usage**:
```bash
# Using justfile (recommended)
just update-docs-version

# Direct execution
python scripts/update_docs_version.py

# Using shell wrapper
./scripts/update_docs_version.sh
```

**Dependencies**: 
- Python 3.7+ with `tomllib` (Python 3.11+) or `tomli` package

## update_docs_version.sh

**Purpose**: Shell wrapper for `update_docs_version.py` that handles dependency installation.

**Usage**:
```bash
./scripts/update_docs_version.sh
```

## Integration

### Local Development
Use `just update-docs-version` before building documentation locally.

### CI/CD (GitHub Pages)
The version update is automatically integrated into the GitHub Pages workflow in `.github/workflows/pages.yml`.

### Manual Execution
Both Python script and shell wrapper can be run independently for custom build processes.

## When to Use

- **Before releasing**: Ensure documentation reflects the current version
- **Before building docs**: Keep documentation in sync with package version
- **In CI/CD**: Automatically update version during deployment

The scripts are designed to be idempotent - running them multiple times with the same version will not cause issues.
