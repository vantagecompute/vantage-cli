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
"""REST API client factory for job commands."""

from vantage_cli.vantage_rest_api_client import create_vantage_rest_client
from vantage_cli.config import Settings


def job_rest_client(profile: str, settings: Settings):
    """Create a REST client configured for Jobbergate API."""
    return create_vantage_rest_client(
        base_url=f"{settings.api_base_url}/jobbergate",
        profile=profile
    )