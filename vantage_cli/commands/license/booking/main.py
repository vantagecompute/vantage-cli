"""License booking management commands using the Vantage REST API."""

import json
from pathlib import Path
from typing import Optional

import typer

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.vantage_rest_api_client import (
    create_vantage_rest_client,
)

app = typer.Typer(help="License booking management commands")


@app.command("list")
@attach_settings
@handle_abort
async def list_bookings(
    ctx: typer.Context,
    search: Optional[str] = typer.Option(
        None, "--search", "-s", help="Search bookings by name or id"
    ),
    sort: Optional[str] = typer.Option(
        None, "--sort", help="Sort by field (name, id, created_at)"
    ),
    limit: Optional[int] = typer.Option(
        None, "--limit", "-l", help="Maximum number of bookings to return"
    ),
    offset: Optional[int] = typer.Option(
        None, "--offset", "-o", help="Number of bookings to skip"
    ),
):
    """List all license bookings."""
    create_vantage_rest_client(ctx)
    try:
        params = {}
        if search:
            params["search"] = search
        if sort:
            params["sort"] = sort
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        await ctx.obj.rest_client.get("/bookings", params=params)
    finally:
        # Use UniversalOutputFormatter for consistent list rendering\n        from vantage_cli.render import UniversalOutputFormatter\n        from rich.console import Console\n        console = Console()\n        formatter = UniversalOutputFormatter(console=console, json_output=False)  # TODO: Get actual json_output flag\n        formatter.render_list(\n            data=bookings,\n            resource_name=\"License Bookings\",\n            empty_message=\"No license bookings found.\"\n        )
        await ctx.obj.rest_client.close()


@app.command("get")
@attach_settings
@handle_abort
async def get_booking(
    ctx: typer.Context, booking_id: str = typer.Argument(..., help="Booking ID")
):
    """Get a specific license booking by ID."""
    create_vantage_rest_client(ctx)
    try:
        booking = await ctx.obj.rest_client.get(f"/bookings/{booking_id}")

        # Use UniversalOutputFormatter for consistent get rendering
        from vantage_cli.render import UniversalOutputFormatter

        formatter = UniversalOutputFormatter(
            console=ctx.obj.console, json_output=ctx.obj.json_output
        )
        formatter.render_get(data=booking, resource_name="License Booking", resource_id=booking_id)
    finally:
        await ctx.obj.rest_client.close()


@app.command("create")
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


@app.command("delete")
@attach_settings
@handle_abort
async def delete_booking(
    ctx: typer.Context, booking_id: str = typer.Argument(..., help="Booking ID")
):
    """Delete a license booking."""
    create_vantage_rest_client(ctx)
    try:
        await ctx.obj.rest_client.delete(f"/bookings/{booking_id}")

        # Use UniversalOutputFormatter for consistent delete rendering
        from vantage_cli.render import UniversalOutputFormatter

        formatter = UniversalOutputFormatter(
            console=ctx.obj.console, json_output=ctx.obj.json_output
        )
        formatter.render_delete(
            resource_name="License Booking",
            resource_id=booking_id,
            success_message=f"License booking '{booking_id}' deleted successfully!",
        )
    finally:
        await ctx.obj.rest_client.close()
