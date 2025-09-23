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
"""Update cloud command."""

from pathlib import Path
from typing import Optional

import typer
from typing_extensions import Annotated

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@handle_abort
@attach_settings
async def update_command(
    ctx: typer.Context,
    cloud_name: Annotated[str, typer.Argument(help="Name of the cloud to update")],
    provider: Annotated[
        Optional[str], typer.Option("--provider", "-p", help="Update cloud provider")
    ] = None,
    region: Annotated[
        Optional[str], typer.Option("--region", "-r", help="Update default region")
    ] = None,
    config_file: Annotated[
        Optional[Path],
        typer.Option(
            "--config-file",
            help="Path to updated configuration file",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        ),
    ] = None,
    credentials_file: Annotated[
        Optional[Path],
        typer.Option(
            "--credentials-file",
            help="Path to updated credentials file",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        ),
    ] = None,
    description: Annotated[
        Optional[str], typer.Option("--description", help="Update cloud description")
    ] = None,
):
    """Update an existing cloud configuration."""
    pass
