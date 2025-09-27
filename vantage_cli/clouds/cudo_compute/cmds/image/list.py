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
"""List Cudo Compute images command."""

import logging

import typer

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings

from .. import attach_cudo_compute_client

logger = logging.getLogger(__name__)


@attach_settings
@attach_persona
@attach_cudo_compute_client
async def list_images(
    ctx: typer.Context,
    project_id: str = typer.Option(None, "--project-id", help="Project ID (for private images)"),
    image_type: str = typer.Option("public", "--type", help="Image type: public or private"),
) -> None:
    """List Cudo Compute VM images (public or private)."""
    try:
        if image_type == "private":
            if not project_id:
                logger.debug(
                    "[bold red]Error:[/bold red] --project-id is required for private images"
                )
                raise typer.Exit(code=1)
            images = await ctx.obj.cudo_sdk.list_private_vm_images(project_id=project_id)
        else:
            images = await ctx.obj.cudo_sdk.list_public_vm_images()
    except Exception as e:
        logger.debug(f"[bold red]Error:[/bold red] Failed to list images: {e}")
        raise typer.Exit(code=1)

    if not images:
        logger.debug(f"No {image_type} images found.")
        return

    # Convert Pydantic models to dicts for the formatter
    images_data = [img.model_dump() for img in images]

    ctx.obj.formatter.render_list(
        data=images_data,
        resource_name=f"Cudo Compute {image_type.capitalize()} Images",
    )
