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
"""Get command for cloud provider configurations."""

import typer
from typing_extensions import Annotated

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@handle_abort
@attach_settings
async def get_command(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Name of the cloud configuration to retrieve")],
) -> None:
    """Get details of a specific cloud configuration.

    Retrieves and displays detailed information about a specific cloud provider
    configuration including credentials, region settings, and connection status.

    Args:
        ctx: The Typer context
        name: Name of the cloud configuration to retrieve
    """
    pass
