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
"""Rendering functions for SLURM Multipass localhost deployments."""

from rich.console import Console

__all__ = ["show_deployment_error"]


def show_deployment_error(console: Console, cluster_name: str, error: Exception) -> None:
    """Show deployment error message and troubleshooting steps."""
    console.print()
    console.print("❌ [bold red]SLURM Multipass deployment failed![/bold red]")
    
    # Format error message - handle typer.Exit which converts to exit code
    error_msg = str(error)
    if error_msg and not error_msg.isdigit():  # Skip if it's just an exit code like "1"
        console.print(f"[red]Error: {error_msg}[/red]")
    elif hasattr(error, 'message'):
        console.print(f"[red]Error: {error.message}[/red]")
    
    console.print()
    console.print("[bold]Troubleshooting Steps:[/bold]")
    console.print("• Check Multipass status: [cyan]multipass version[/cyan]")
    console.print("• List existing VMs: [cyan]multipass list[/cyan]")
    console.print("• Check VM logs: [cyan]multipass info <vm-name> --format yaml[/cyan]")
    console.print("• Delete failed VM: [cyan]multipass delete <vm-name> --purge[/cyan]")
    console.print(
        f"• Retry with verbose output: [cyan]vantage app deployment slurm-multipass-localhost create {cluster_name} --verbose[/cyan]"
    )
    console.print(
        "• Remove failed deployment: [cyan]vantage app deployment slurm-multipass-localhost remove <deployment-name>[/cyan]"
    )
    console.print()
