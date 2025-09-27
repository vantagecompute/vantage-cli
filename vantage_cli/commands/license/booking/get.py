"""Get license booking command using the Vantage REST API."""

import typer

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.render import UniversalOutputFormatter
from vantage_cli.sdk.license import license_booking_sdk
from vantage_cli.vantage_rest_api_client import attach_vantage_rest_client


@handle_abort
@attach_settings
@attach_persona
@attach_vantage_rest_client(base_path="/lm")
async def get_booking(
    ctx: typer.Context, booking_id: str = typer.Argument(..., help="Booking ID")
):
    """Get a specific license booking by ID."""
    # Use SDK to get license booking
    response = await license_booking_sdk.get(ctx, booking_id)

    # Use UniversalOutputFormatter for consistent get rendering
    formatter = UniversalOutputFormatter(console=ctx.obj.console, json_output=ctx.obj.json_output)
    formatter.render_get(data=response, resource_name="License Booking", resource_id=booking_id)
