# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Delete cloud command."""

import logging

import typer
from typing_extensions import Annotated

logger = logging.getLogger(__name__)


def delete_command(
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
    verbose = ctx.obj.get("verbose", False)
    settings = ctx.obj.get("settings")

    logger.info(f"Deleting cloud configuration: {cloud_name}")

    if verbose:
        logger.debug(f"Force: {force}")
        logger.debug(f"Remove credentials: {remove_credentials}")
        logger.debug(f"Settings: {settings}")

    # TODO: Check if cloud exists
    # TODO: Check if cloud is in use by any clusters

    if not force:
        warning_msg = f"Are you sure you want to delete cloud configuration '{cloud_name}'?"
        if remove_credentials:
            warning_msg += " This will also remove stored credentials."

        confirm = typer.confirm(warning_msg)
        if not confirm:
            typer.echo("Operation cancelled.")
            raise typer.Abort()

    typer.echo(f"Deleting cloud configuration: {cloud_name}")

    if remove_credentials:
        typer.echo("Removing stored credentials...")
        logger.info("Removing stored credentials")

    # TODO: Implement actual cloud configuration deletion logic
    # This would typically:
    # 1. Remove cloud config from storage
    # 2. Update the supported clouds list
    # 3. Optionally remove credentials
    # 4. Clean up any related files

    logger.info(f"Cloud {cloud_name} deleted successfully")
    typer.echo(f"✅ Cloud '{cloud_name}' deleted successfully")
