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
"""Alias command for apps -> deployment list."""

from typing import Optional

import typer
from typing_extensions import Annotated

from vantage_cli.commands.deployment.list import list_deployments
from vantage_cli.exceptions import handle_abort


@handle_abort
async def deployments_command(
    ctx: typer.Context,
    cloud: Annotated[
        Optional[str],
        typer.Option(
            "--cloud", help="Filter deployments by cloud type (e.g., localhost, aws, gcp)"
        ),
    ] = None,
):
    """List all deployments (alias for 'vantage deployment list')."""
    await list_deployments(ctx, cloud=cloud)
