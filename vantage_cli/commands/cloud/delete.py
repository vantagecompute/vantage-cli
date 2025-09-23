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
"""Delete cloud command."""

import typer
from typing_extensions import Annotated

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@handle_abort
@attach_settings
async def delete_command(
    ctx: typer.Context,
    cloud_name: Annotated[str, typer.Argument(help="Name of the cloud to delete")],
    force: Annotated[
        bool, typer.Option("--force", help="Force deletion without confirmation")
    ] = False,
    remove_credentials: Annotated[
        bool, typer.Option("--remove-credentials", help="Also remove stored credentials")
    ] = False,
):
    """Delete a cloud configuration."""
    pass
