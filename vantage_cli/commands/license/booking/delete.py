"""Delete license booking command using the Vantage REST API."""

import typer

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.vantage_rest_api_client import (
    create_vantage_rest_client,
)


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
