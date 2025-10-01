"""Get license booking command using the Vantage REST API.
"""

import typer

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.vantage_rest_api_client import create_vantage_rest_client


@attach_settings
@handle_abort
async def get_booking(
    ctx: typer.Context, booking_id: str = typer.Argument(..., help="Booking ID")
):
    """Get a specific license booking by ID."""
    client = create_vantage_rest_client()
    try:
        booking = await client.get(f"/bookings/{booking_id}")

        # Use UniversalOutputFormatter for consistent get rendering
        from vantage_cli.render import UniversalOutputFormatter

        formatter = UniversalOutputFormatter(
            console=ctx.obj.console, json_output=ctx.obj.json_output
        )
        formatter.render_get(data=booking, resource_name="License Booking", resource_id=booking_id)
    finally:
        await client.close()
