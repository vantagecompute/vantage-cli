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
"""Create federation command."""

import typer
from typing_extensions import Annotated

from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.render import RenderStepOutput


@attach_settings
@handle_abort
async def create_federation(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Name of the federation to create")],
    description: Annotated[
        str, typer.Option("--description", "-d", help="Description of the federation")
    ] = "",
    command_start_time: float = 0.0,
):
    """Create a new Vantage federation."""
    json_output = getattr(ctx.obj, "json_output", False)

    renderer = RenderStepOutput(
        console=ctx.obj.console,
        operation_name=f"Create Federation '{name}'",
        step_names=[] if json_output else ["Creating federation"],
        command_start_time=command_start_time,
    )

    federation_data = {
        "name": name,
        "description": description,
        "status": "created",
        "message": "Federation create command not yet implemented",
    }

    if json_output:
        renderer.json_bypass(federation_data)
    else:
        with renderer:
            renderer.advance("Creating federation")
            ctx.obj.console.print("🔗 [bold blue]Federation Create Command[/bold blue]")
            ctx.obj.console.print(f"📝 Creating federation: [bold]{name}[/bold]")
            if description:
                ctx.obj.console.print(f"📋 Description: {description}")
            ctx.obj.console.print("⚠️  [yellow]Not yet implemented - this is a stub[/yellow]")
