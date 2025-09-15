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

# Install Docusaurus dependencies
[group("docusaurus")]
docs-install:
    @echo "📦 Installing Docusaurus dependencies..."
    cd docs && yarn install

# Start Docusaurus development server
[group("docusaurus")]
docs-dev: docs-install
    @echo "🚀 Starting Docusaurus development server..."
    cd docs && yarn start

# Start Docusaurus development server on specific port
[group("docusaurus")]
docs-dev-port port="3000": docs-install
    @echo "🚀 Starting Docusaurus development server on port {{port}}..."
    cd docs && yarn start --port {{port}}

# Build Docusaurus for production
[group("docusaurus")]
docs-build: docs-install
    @echo "🏗️ Building Docusaurus for production..."
    cd docs && yarn build

# Serve built Docusaurus site locally
[group("docusaurus")]
docs-serve: docs-build
    @echo "🌐 Serving built Docusaurus site..."
    cd docs && yarn serve

# Clean Docusaurus build artifacts
[group("docusaurus")]
docs-clean:
    @echo "🧹 Cleaning Docusaurus build artifacts..."
    cd docs && rm -rf build .docusaurus

# Show available documentation commands
[group("docusaurus")]
docs-help:
    @echo "📚 Docusaurus Commands:"
    @echo "  docs-install    - Install dependencies"
    @echo "  docs-dev        - Start development server"
    @echo "  docs-dev-port   - Start dev server on specific port"
    @echo "  docs-build      - Build for production"
    @echo "  docs-serve      - Serve built site"
    @echo "  docs-clean      - Clean build artifacts"

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
    {{uv_run}} coverage report --fail-under=80
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
