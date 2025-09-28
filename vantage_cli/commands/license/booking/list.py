"""
List license bookings command using the License Manager API.
"""
import typer
from typing import Optional
from vantage_cli.vantage_rest_api_client import create_vantage_rest_client
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort


@attach_settings
@handle_abort
async def list_bookings(
    ctx: typer.Context,
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search bookings by name or id"),
    sort: Optional[str] = typer.Option(None, "--sort", help="Sort by field (name, id, created_at)"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Maximum number of bookings to return"),
    offset: Optional[int] = typer.Option(None, "--offset", "-o", help="Number of bookings to skip")
):
    """List all license bookings."""
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
        
        # Use UniversalOutputFormatter for consistent list rendering
        from vantage_cli.render import UniversalOutputFormatter
        formatter = UniversalOutputFormatter(console=ctx.obj.console, json_output=ctx.obj.json_output)
        formatter.render_list(
            data=bookings,
            resource_name="License Bookings",
            empty_message="No license bookings found."
        )
    finally:
        await client.close()