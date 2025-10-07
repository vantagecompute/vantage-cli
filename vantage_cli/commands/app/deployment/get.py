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
from vantage_cli.exceptions import handle_abort
from vantage_cli.render import RenderStepOutput
from vantage_cli.sdk.deployment import deployment_sdk

from .render import render_deployment_details


@attach_settings
@handle_abort
async def get_deployment(
    ctx: typer.Context,
    deployment_id: Annotated[str, typer.Argument(help="ID or name of the deployment to retrieve")],
) -> None:
    """Get detailed information about a specific deployment."""
    # Get JSON flag from context (automatically set by AsyncTyper)
    json_output = getattr(ctx.obj, "json_output", False)
    verbose = getattr(ctx.obj, "verbose", False)

    try:
        # Get command start time for timing
        command_start_time = getattr(ctx.obj, "command_start_time", None) if ctx.obj else None

        # Rich output with progress system
        renderer = RenderStepOutput(
            console=ctx.obj.console,
            operation_name=f"Getting deployment '{deployment_id}'",
            step_names=["Fetching deployment details", "Complete"],
            verbose=verbose,
            command_start_time=command_start_time,
        )

        with renderer:
            # Step 1: Load deployment data
            renderer.start_step("Fetching deployment details")

            # Try to get deployment details (which includes all fields)
            deployment_details = await deployment_sdk.get_deployment_details(ctx, deployment_id)

            if deployment_details is None:
                # Try searching by deployment name in case user provided a name instead of ID
                deployments = await deployment_sdk.list(ctx)
                for dep in deployments:
                    if dep.get("deployment_name") == deployment_id:
                        deployment_details = await deployment_sdk.get_deployment_details(
                            ctx, dep.get("deployment_id", "")
                        )
                        break

                if deployment_details is None:
                    ctx.obj.console.print(f"[red]Deployment '{deployment_id}' not found.[/red]")
                    ctx.obj.console.print(
                        "[dim]Use 'vantage deployment list' to see available deployments.[/dim]"
                    )
                    raise typer.Exit(1)

            # Handle JSON output first
            if json_output:
                renderer.json_bypass(deployment_details)
                return

            # Step 2: Render the deployment details table
            renderer.table_step(render_deployment_details(deployment_details))
            renderer.complete_step("Complete")

    except Exception as e:
        ctx.obj.console.print(f"[red]Error retrieving deployment: {e}[/red]")
        raise typer.Exit(1)
