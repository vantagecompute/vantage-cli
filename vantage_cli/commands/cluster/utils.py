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
"""Shared utilities for cluster commands."""

from vantage_cli.config import Settings


def get_cloud_choices() -> list[str]:
    """Get the list of supported clouds from settings."""
    settings = Settings()
    return settings.supported_clouds


def get_app_choices() -> list[str]:
    """Get the list of available deployment apps."""
    try:
        # Import SDK here to avoid module-level initialization
        from vantage_cli.sdk.deployment_app import deployment_app_sdk

        apps = deployment_app_sdk.list()
        choices = [app.name for app in apps]
        return choices
    except Exception:
        return []
