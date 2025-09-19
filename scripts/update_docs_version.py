#!/usr/bin/env python3
"""
Simple script to update Docusaurus version.yml from pyproject.toml
"""

import re
import subprocess
from datetime import datetime
from pathlib import Path


def get_version_from_pyproject():
    """Extract version from pyproject.toml"""
    pyproject_path = Path("pyproject.toml")
    content = pyproject_path.read_text()
    match = re.search(r'^version = "([^"]+)"', content, re.MULTILINE)
    if not match:
        raise ValueError("Could not find version in pyproject.toml")
    return match.group(1)


def get_git_commit():
    """Get current git commit hash"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return "unknown"


def update_version_yml():
    """Update the Docusaurus version.yml file"""
    version = get_version_from_pyproject()
    date = datetime.now().strftime("%Y-%m-%d")
    commit = get_git_commit()
    build_number = datetime.now().strftime("%Y%m%d%H%M")
    
    version_yml_content = f"""# Vantage CLI Version Information
# This file is automatically updated by GitHub Actions
# Do not manually edit this file

version: "{version}"
lastUpdated: "{date}"
buildNumber: "{build_number}"
gitCommit: "{commit}"
releaseDate: "{date}"
"""
    
    version_yml_path = Path("docusaurus/data/version.yml")
    version_yml_path.write_text(version_yml_content)
    
    print(f"✓ Updated docusaurus/data/version.yml with version {version} (build: {build_number}, commit: {commit})")


if __name__ == "__main__":
    update_version_yml()
