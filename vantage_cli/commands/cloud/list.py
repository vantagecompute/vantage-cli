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
"""List command for cloud provider configurations."""

import typer

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@handle_abort
@attach_settings
async def list_command(
    ctx: typer.Context,
) -> None:
    """List all available cloud providers.

    Displays all cloud providers configured in the system, including their
    Vantage provider labels and supported substrates (infrastructure types).

    Examples:
        List all clouds:
        $ vantage cloud list

        Using the alias:
        $ vantage clouds
    """
    # Import SDK here to avoid module-level initialization
    from vantage_cli.sdk.cloud import cloud_sdk

    # Get all clouds from SDK
    clouds = cloud_sdk.list(enabled_only=False)

    # Prepare cloud data for output
    clouds_data = []
    for cloud in clouds:
        cloud_data = {
            "name": cloud.name,
            "label": cloud.vantage_provider_label,
            "substrates": ", ".join(cloud.substrates),
            "enabled": "Yes" if cloud.enabled else "No",
        }
        clouds_data.append(cloud_data)

    # Use UniversalOutputFormatter for consistent list rendering
    ctx.obj.formatter.render_list(
        data=clouds_data, resource_name="Clouds", empty_message="No clouds found."
    )
