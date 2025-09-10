#!/usr/bin/env just --justfile

uv := require("uv")

project_dir := justfile_directory()
src_dir := project_dir / "vantage_cli"
tests_dir := project_dir / "tests"

export PY_COLORS := "1"
export PYTHONBREAKPOINT := "pdb.set_trace"
export PYTHONPATH := src_dir

uv_run := "uv run --frozen --extra dev"

[private]
default:
    @just help

# Regenerate uv.lock
[group("dev")]
lock:
    uv lock

# Update documentation files with current version from pyproject.toml
[group("docs")]
update-docs-version:
    #!/usr/bin/env bash
    set -euo pipefail
    # Extract version from pyproject.toml
    VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
    TODAY=$(date +%Y-%m-%d)
    echo "📝 Updating docs with version: $VERSION (date: $TODAY)"
    
    # Update docs/_data/project.yml
    sed -i "s/^version: .*/version: \"$VERSION\"/" docs/_data/project.yml
    sed -i "s/^updated: .*/updated: \"$TODAY\"/" docs/_data/project.yml
    
    # Update docs/_config.yml (add version if missing, update if exists)
    if grep -q "^version:" docs/_config.yml; then
        sed -i "s/^version: .*/version: \"$VERSION\"/" docs/_config.yml
    else
        sed -i "/^description:/a version: \"$VERSION\"" docs/_config.yml
    fi
    
    # Update docs/index.md front matter (add version if missing, update if exists)
    if grep -q "^version:" docs/index.md; then
        sed -i "s/^version: .*/version: \"$VERSION\"/" docs/index.md
    else
        sed -i "/^permalink:/a version: \"$VERSION\"" docs/index.md
    fi
    
    echo "✅ Updated documentation files with version $VERSION"

# Build documentation with updated version  
[group("docs")]
build-docs: update-docs-version
    @echo "📚 Documentation version updated. Ready for Jekyll build."

# Run static type checker on code
[group("lint")]
typecheck: lock
    {{uv_run}} pyright {{src_dir}}


# Apply coding style standards to code
[group("lint")]
fmt: lock
    {{uv_run}} ruff format {{src_dir}} {{tests_dir}}
    {{uv_run}} ruff check --fix {{src_dir}} {{tests_dir}}

# Check code against coding style standards
[group("lint")]
lint: lock
    {{uv_run}} codespell {{src_dir}}
    {{uv_run}} ruff check {{src_dir}} {{tests_dir}}

# Run unit tests
[group("test")]
unit *args: lock
    {{uv_run}} coverage run \
        --source {{src_dir}} \
        -m pytest \
        --tb native \
        -v -s {{args}} {{tests_dir / "unit"}}
    {{uv_run}} coverage report --fail-under=90
    {{uv_run}} coverage xml -o {{project_dir / "cover_unit" / "coverage.xml"}}

# Run integration tests
[group("test")]
integration *args: lock
    {{uv_run}} coverage run \
        --source {{src_dir}} \
        -m pytest \
        --tb native \
        -v -s {{args}} {{tests_dir / "integration"}}
    {{uv_run}} coverage report --fail-under=0
    {{uv_run}} coverage xml -o {{project_dir / "cover_integration" / "coverage.xml"}}

# Run full (unit + integration) test suite with combined coverage
[group("test")]
coverage-all *args: lock
    mkdir -p {{project_dir / "cover_combined"}}
    {{uv_run}} coverage erase
    # Unit tests (parallel data file)
    if [ -d "{{tests_dir / "unit"}}" ]; then \
        {{uv_run}} coverage run -p --source {{src_dir}} -m pytest --tb native -v -s {{args}} {{tests_dir / "unit"}}; \
    fi
    # Integration tests (parallel data file, only if directory exists)
    if [ -d "{{tests_dir / "integration"}}" ]; then \
        {{uv_run}} coverage run -p --source {{src_dir}} -m pytest --tb native -v -s {{args}} {{tests_dir / "integration"}}; \
    fi
    # Combine parallel data files & report (no fail threshold for combined coverage)
    {{uv_run}} coverage combine
    {{uv_run}} coverage report --fail-under=0
    {{uv_run}} coverage xml -o {{project_dir / "cover_combined" / "coverage.xml"}}
