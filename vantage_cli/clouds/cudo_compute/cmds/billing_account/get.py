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
"""Get Cudo Compute billing account command."""

import logging

import typer

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings

from .. import attach_cudo_compute_client

logger = logging.getLogger(__name__)


@attach_settings
@attach_persona
@attach_cudo_compute_client
async def get_billing_account(
    ctx: typer.Context,
    billing_account_id: str = typer.Argument(..., help="Billing account ID"),
) -> None:
    """Get details of a specific Cudo Compute billing account."""
    try:
        billing_account = await ctx.obj.cudo_sdk.get_billing_account(
            billing_account_id=billing_account_id
        )
    except Exception as e:
        logger.debug(f"[bold red]Error:[/bold red] Failed to get billing account: {e}")
        raise typer.Exit(code=1)

    # Convert Pydantic model to dict for the formatter
    billing_account_data = billing_account.model_dump() if billing_account else {}

    ctx.obj.formatter.render_get(
        data=billing_account_data,
        resource_name=f"Billing Account: {billing_account_id}",
    )
