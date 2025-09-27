"""Create license booking command using the Vantage REST API."""

import json
from pathlib import Path
from typing import Optional

import typer

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.vantage_rest_api_client import (
    create_vantage_rest_client,
)


@attach_settings
@handle_abort
async def create_booking(
    ctx: typer.Context,
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Booking name"),
    description: Optional[str] = typer.Option(
        None, "--description", "-d", help="Booking description"
    ),
    json_file: Optional[Path] = typer.Option(
        None, "--json-file", "-f", help="JSON file with booking data"
    ),
):
    """Create a new license booking."""
    create_vantage_rest_client(ctx)
    try:
        if json_file:
            if not json_file.exists():
                typer.echo(f"Error: File {json_file} does not exist", err=True)
                raise typer.Exit(1)
            with open(json_file, "r") as f:
                data = json.load(f)
        else:
            if not name:
                typer.echo("Error: --name is required when not using --json-file", err=True)
                raise typer.Exit(1)
            data = {"name": name}
            if description:
                data["description"] = description

        booking = await ctx.obj.rest_client.post("/bookings", json=data)

        # Use UniversalOutputFormatter for consistent create rendering
        from vantage_cli.render import UniversalOutputFormatter

        formatter = UniversalOutputFormatter(
            console=ctx.obj.console, json_output=ctx.obj.json_output
        )
        formatter.render_create(
            data=booking,
            resource_name="License Booking",
            success_message="License booking created successfully!",
        )
    finally:
        await ctx.obj.rest_client.close()
