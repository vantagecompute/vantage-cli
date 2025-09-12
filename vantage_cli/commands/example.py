# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Example command showing the new standardized pattern for JSON options."""

import typer
from rich import print_json
from rich.console import Console
from typing_extensions import Annotated

from vantage_cli.command_base import JsonOption, VerboseOption
from vantage_cli.command_utils import should_use_json

# Define ForceOption locally since it's not in the main codebase
ForceOption = Annotated[bool, typer.Option("--force", "-f", help="Force the operation")]

console = Console()


async def example_command(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Name of the resource")],
    description: Annotated[
        str, typer.Option("--description", "-d", help="Description of the resource")
    ] = "",
    json_output: JsonOption = False,
    verbose: VerboseOption = False,
    force: ForceOption = False,
):
    """Show standardized option handling.

    This command demonstrates the recommended pattern for using consistent
    JSON, verbose, and force options across all CLI commands.
    """
    # Determine output format using the utility function
    use_json = should_use_json(ctx)

    # Check verbose mode (local flag or global setting)
    is_verbose = verbose or getattr(ctx.obj, "verbose", False)

    # Mock operation result
    result = {
        "name": name,
        "description": description,
        "status": "created" if not force else "force-created",
        "timestamp": "2025-09-12T10:00:00Z",
        "verbose_mode": is_verbose,
    }

    if use_json:
        print_json(data=result)
    else:
        console.print("🎯 [bold blue]Example Command Result[/bold blue]")
        console.print(f"📝 Name: [bold]{name}[/bold]")

        if description:
            console.print(f"📋 Description: {description}")

        console.print(f"✅ Status: [green]{result['status']}[/green]")
        console.print(f"🕐 Timestamp: {result['timestamp']}")

        if is_verbose:
            console.print("🔍 [dim]Verbose mode enabled[/dim]")
            console.print(f"🔧 [dim]Force flag: {force}[/dim]")
            console.print(f"🔧 [dim]JSON output: {json_output}[/dim]")


if __name__ == "__main__":
    # This would be registered in the main app
    app = typer.Typer()
    app.command("example")(example_command)
    app()
