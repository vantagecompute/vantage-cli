"""List license bookings command using the License Manager API."""

from typing import Optional

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
    # Use SDK to list license bookings
    response = await license_booking_sdk.list(
        ctx, search=search, sort=sort, limit=limit, offset=offset
    )

    # Use UniversalOutputFormatter for consistent list rendering
    formatter = UniversalOutputFormatter(console=ctx.obj.console, json_output=ctx.obj.json_output)
    formatter.render_list(
        data=response,
        resource_name="License Bookings",
        empty_message="No license bookings found.",
    )
