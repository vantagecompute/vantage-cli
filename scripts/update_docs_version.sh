#!/bin/bash
# Update documentation version from pyproject.toml
# This script can be run locally or in CI/CD

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🔄 Updating documentation version..."

# Check if we're in a Python environment with the required packages
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    echo "❌ Error: Python not found"
    exit 1
fi

# Try to run the update script
cd "$PROJECT_ROOT"

# Check if tomli/tomllib is available
if ! $PYTHON_CMD -c "import sys; import tomllib if sys.version_info >= (3, 11) else __import__('tomli')" 2>/dev/null; then
    echo "📦 Installing tomli for Python < 3.11..."
    # Try different installation methods
    if command -v pip >/dev/null 2>&1; then
        pip install --quiet tomli
    elif command -v pip3 >/dev/null 2>&1; then
        pip3 install --quiet tomli
    elif $PYTHON_CMD -m pip --version >/dev/null 2>&1; then
        $PYTHON_CMD -m pip install --quiet tomli
    else
        echo "⚠️  Warning: Could not install tomli. Script may fail for Python < 3.11"
    fi
fi

# Run the update script
$PYTHON_CMD scripts/update_docs_version.py

echo "✅ Documentation version update complete!"
