#!/usr/bin/env python3
"""
Update documentation files with version from pyproject.toml

This script reads the version from pyproject.toml and updates:
1. docs/_data/project.yml (replaces __VERSION__ placeholder)
2. docs/_config.yml (adds version field)
3. Any other documentation files that need version updates
"""

import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

try:
    import tomllib
except ImportError:
    # Python < 3.11 fallback
    try:
        import tomli as tomllib
    except ImportError:
        print("Error: tomllib (Python 3.11+) or tomli package required")
        sys.exit(1)


def load_pyproject_version() -> str:
    """Load version from pyproject.toml"""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    
    if not pyproject_path.exists():
        raise FileNotFoundError(f"pyproject.toml not found at {pyproject_path}")
    
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    
    version = data.get("project", {}).get("version")
    if not version:
        raise ValueError("Version not found in pyproject.toml")
    
    return version


def update_project_yml(version: str) -> None:
    """Update docs/_data/project.yml with the current version"""
    project_yml_path = Path(__file__).parent.parent / "docs" / "_data" / "project.yml"
    
    if not project_yml_path.exists():
        print(f"Warning: {project_yml_path} not found, skipping")
        return
    
    content = project_yml_path.read_text(encoding="utf-8")
    
    # Replace version placeholder
    updated_content = re.sub(
        r'version:\s*["\']?__VERSION__["\']?',
        f'version: "{version}"',
        content
    )
    
    # Update the date as well
    today = datetime.now().strftime("%Y-%m-%d")
    updated_content = re.sub(
        r'updated:\s*["\']?[\d-]+["\']?',
        f'updated: "{today}"',
        updated_content
    )
    
    project_yml_path.write_text(updated_content, encoding="utf-8")
    print(f"✓ Updated {project_yml_path} with version {version}")


def update_config_yml(version: str) -> None:
    """Update docs/_config.yml with the current version"""
    config_yml_path = Path(__file__).parent.parent / "docs" / "_config.yml"
    
    if not config_yml_path.exists():
        print(f"Warning: {config_yml_path} not found, skipping")
        return
    
    content = config_yml_path.read_text(encoding="utf-8")
    
    # Check if version field already exists
    if re.search(r'^version:\s*', content, re.MULTILINE):
        # Update existing version
        updated_content = re.sub(
            r'^version:\s*.*$',
            f'version: "{version}"',
            content,
            flags=re.MULTILINE
        )
    else:
        # Add version field after description
        updated_content = re.sub(
            r'(description:.*?\n)',
            f'\\1version: "{version}"\n',
            content,
            flags=re.DOTALL
        )
    
    config_yml_path.write_text(updated_content, encoding="utf-8")
    print(f"✓ Updated {config_yml_path} with version {version}")


def update_index_md(version: str) -> None:
    """Update docs/index.md with version information if needed"""
    index_md_path = Path(__file__).parent.parent / "docs" / "index.md"
    
    if not index_md_path.exists():
        print(f"Warning: {index_md_path} not found, skipping")
        return
    
    content = index_md_path.read_text(encoding="utf-8")
    
    # Add version to the front matter if it doesn't exist
    if "version:" not in content and "---" in content:
        # Insert version into front matter
        updated_content = re.sub(
            r'(---\n.*?)\n(---)',
            f'\\1\nversion: "{version}"\n\\2',
            content,
            flags=re.DOTALL
        )
        
        if updated_content != content:
            index_md_path.write_text(updated_content, encoding="utf-8")
            print(f"✓ Updated {index_md_path} with version {version}")


def main() -> None:
    """Main function to update all documentation files with version"""
    try:
        version = load_pyproject_version()
        print(f"📝 Updating documentation with version: {version}")
        
        # Update all documentation files
        update_project_yml(version)
        update_config_yml(version)
        update_index_md(version)
        
        print(f"🎉 Successfully updated documentation files with version {version}")
        
    except Exception as e:
        print(f"❌ Error updating documentation version: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
