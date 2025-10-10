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
"""REST API client factory for license commands."""

import typer

from vantage_cli.vantage_rest_api_client import create_vantage_rest_client


def lm_rest_client(ctx: typer.Context):
    """Create a REST client configured for License Manager API.

    Args:
        ctx: Typer context containing settings and persona

    Returns:
        VantageRestApiClient configured for license manager endpoints
    """
    return create_vantage_rest_client(ctx)
