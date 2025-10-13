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
"""Get detailed information about a specific deployment."""

import typer
from typing_extensions import Annotated

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import Abort, handle_abort
from vantage_cli.sdk.deployment import deployment_sdk


@attach_settings
@handle_abort
async def get_deployment(
    ctx: typer.Context,
    deployment_id: Annotated[str, typer.Argument(help="ID or name of the deployment to retrieve")],
) -> None:
    """Get detailed information about a specific deployment."""
    try:
        # Try to get deployment details
        deployment = await deployment_sdk.get_deployment(ctx, deployment_id)

        if deployment is None:
            raise Abort(
                f"Deployment '{deployment_id}' not found.",
                subject="Deployment Not Found",
                log_message=f"Deployment not found: {deployment_id}",
                hint="Use 'vantage app deployment list' to see available deployments.",
            )
        # Use the formatter to render the get response
        ctx.obj.formatter.render_get(
            data=deployment.model_dump(mode="json"),
            resource_name="Deployment",
        )

    except Abort:
        raise
    except Exception as e:
        raise Abort(
            f"Failed to retrieve deployment: {e}",
            subject="Get Deployment Error",
            log_message=f"Deployment get error: {e}",
        )
