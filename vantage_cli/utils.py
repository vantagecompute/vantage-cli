# Copyright (C) 2025 Vantage Compute Corporation
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.
"""Utilities for Vantage CLI."""

import os
from typing import Optional


def get_dev_apps_gh_url() -> Optional[str]:
    """Construct the GitHub URL for the dev apps repository."""
    if gh_pat := os.environ.get("GH_PAT"):
        return f"https://{gh_pat}@github.com/vantagecompute/vantage-cli-dev-apps.git"
    return None
