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
"""Add cloud command."""

import logging
from pathlib import Path
from typing import Optional

import typer
from typing_extensions import Annotated

logger = logging.getLogger(__name__)


def add_command(
    ctx: typer.Context,
    cloud_name: Annotated[str, typer.Argument(help="Name of the cloud to add")],
    provider: Annotated[
        str, typer.Option("--provider", "-p", help="Cloud provider (aws, gcp, azure, etc.)")
    ],
    region: Annotated[
        Optional[str], typer.Option("--region", "-r", help="Default region for the cloud")
    ] = None,
    config_file: Annotated[
        Optional[Path],
        typer.Option(
            "--config-file",
            help="Path to cloud configuration file",
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
            help="Path to credentials file",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        ),
    ] = None,
):
    """Add a new cloud configuration."""
    verbose = ctx.obj.get("verbose", False)
    settings = ctx.obj.get("settings")

    logger.info(f"Adding cloud configuration: {cloud_name}")

    if verbose:
        logger.debug(f"Provider: {provider}")
        logger.debug(f"Region: {region}")
        logger.debug(f"Config file: {config_file}")
        logger.debug(f"Credentials file: {credentials_file}")
        logger.debug(f"Settings: {settings}")

    # TODO: Validate that cloud doesn't already exist

    if config_file:
        logger.info(f"Using config file: {config_file}")
        typer.echo(f"Adding cloud '{cloud_name}' with config file: {config_file}")
    else:
        typer.echo(f"Adding cloud '{cloud_name}' with provider: {provider}")
        if region:
            typer.echo(f"Default region: {region}")

    if credentials_file:
        logger.info(f"Using credentials file: {credentials_file}")
        typer.echo(f"Credentials file: {credentials_file}")

    # TODO: Implement actual cloud configuration addition logic
    # This would typically:
    # 1. Validate the cloud configuration
    # 2. Store the cloud config in the appropriate location
    # 3. Update the supported clouds list

    logger.info(f"Cloud {cloud_name} added successfully")
    typer.echo(f"✅ Cloud '{cloud_name}' added successfully")
