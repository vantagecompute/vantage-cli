"""
License booking management commands using the Vantage REST API.
"""
import typer
import asyncio
import json
from pathlib import Path
from typing import Optional
from vantage_cli.vantage_rest_api_client import create_vantage_rest_client
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort

app = typer.Typer(help="License booking management commands")

@app.command("list")
@attach_settings
@handle_abort
def list_bookings(
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search bookings by name or id"),
    sort: Optional[str] = typer.Option(None, "--sort", help="Sort by field (name, id, created_at)"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Maximum number of bookings to return"),
    offset: Optional[int] = typer.Option(None, "--offset", "-o", help="Number of bookings to skip")
):
    """List all license bookings."""
    async def _list_bookings():
        client = create_vantage_rest_client()
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
            bookings = await client.get("/bookings", params=params)
            client.print_json(bookings)
        finally:
            await client.close()
    
    asyncio.run(_list_bookings())

@app.command("get")
@attach_settings
@handle_abort
def get_booking(booking_id: str = typer.Argument(..., help="Booking ID")):
    """Get a specific license booking by ID."""
    async def _get_booking():
        client = create_vantage_rest_client()
        try:
            booking = await client.get(f"/bookings/{booking_id}")
            client.print_json(booking)
        finally:
            await client.close()
    
    asyncio.run(_get_booking())

@app.command("create")
@attach_settings
@handle_abort
def create_booking(
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Booking name"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Booking description"),
    json_file: Optional[Path] = typer.Option(None, "--json-file", "-f", help="JSON file with booking data")
):
    """Create a new license booking."""
    async def _create_booking():
        client = create_vantage_rest_client()
        try:
            if json_file:
                if not json_file.exists():
                    typer.echo(f"Error: File {json_file} does not exist", err=True)
                    raise typer.Exit(1)
                with open(json_file, 'r') as f:
                    data = json.load(f)
            else:
                if not name:
                    typer.echo("Error: --name is required when not using --json-file", err=True)
                    raise typer.Exit(1)
                data = {"name": name}
                if description:
                    data["description"] = description
            
            booking = await client.post("/bookings", json=data)
            client.print_json(booking)
        finally:
            await client.close()
    
    asyncio.run(_create_booking())

@app.command("delete")
@attach_settings
@handle_abort
def delete_booking(booking_id: str = typer.Argument(..., help="Booking ID")):
    """Delete a license booking."""
    async def _delete_booking():
        client = create_vantage_rest_client()
        try:
            await client.delete(f"/bookings/{booking_id}")
            typer.echo(f"Booking {booking_id} deleted successfully")
        finally:
            await client.close()
    
    asyncio.run(_delete_booking())
