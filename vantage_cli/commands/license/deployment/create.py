# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Create license deployment command."""

from typing import Annotated, Optional

import typer
from rich import print_json
from rich.console import Console

from vantage_cli.command_base import get_effective_json_output
from vantage_cli.config import attach_settings

console = Console()


@attach_settings
async def create_license_deployment(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Name of the license deployment to create")],
    product_id: Annotated[
        str, typer.Option("--product-id", "-p", help="Product ID for the deployment")
    ],
    environment: Annotated[
        str, typer.Option("--environment", "-e", help="Deployment environment (dev, test, prod)")
    ] = "dev",
    nodes: Annotated[
        Optional[int], typer.Option("--nodes", "-n", help="Number of nodes in the deployment")
    ] = 1,
    description: Annotated[
        Optional[str],
        typer.Option("--description", "-d", help="Description of the license deployment"),
    ] = None,
):
    """Create a new license deployment."""
    if get_effective_json_output(ctx):
        # JSON output
        print_json(
            data={
                "deployment_id": "deployment-new-123",
                "name": name,
                "product_id": product_id,
                "environment": environment,
                "nodes": nodes,
                "description": description,
                "status": "created",
                "created_at": "2025-09-10T10:00:00Z",
            }
        )
    else:
        # Rich console output
        console.print(f"📦 Creating license deployment [bold blue]{name}[/bold blue]")
        console.print(f"   Product ID: [green]{product_id}[/green]")
        console.print(f"   Environment: [yellow]{environment}[/yellow]")
        console.print(f"   Nodes: [cyan]{nodes}[/cyan]")
        if description:
            console.print(f"   Description: {description}")
        console.print("✅ License deployment created successfully!")
