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

from textwrap import dedent

from rich.console import Console

from vantage_cli.sdk.deployment.schema import Deployment

__all__ = ["show_deployment_error", "success_create_message"]


def show_deployment_error(console: Console, cluster_name: str, error: Exception) -> None:
    """Show deployment error message and troubleshooting steps."""
    console.print()
    console.print("❌ [bold red]SLURM Multipass deployment failed![/bold red]")

    # Format error message - handle typer.Exit which converts to exit code
    error_msg = str(error)
    if error_msg and not error_msg.isdigit():  # Skip if it's just an exit code like "1"
        console.print(f"[red]Error: {error_msg}[/red]")
    elif hasattr(error, "__dict__") and "message" in error.__dict__:
        console.print(f"[red]Error: {error.__dict__['message']}[/red]")

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


def success_create_message(deployment: Deployment) -> str:
    """Generate success message for Multipass SLURM deployment.

    Args:
        deployment: Deployment object containing cluster and deployment information

    Returns:
        Formatted success message with deployment details and access instructions
    """
    instance_name = deployment.name
    cluster_name = deployment.cluster.name
    client_id = deployment.cluster.client_id

    return dedent(
        f"""\
        🎉 [bold green]SLURM Multipass deployment completed successfully![/bold green]

        Access your cluster in the Vantage UI: [cyan]https://app.vantagecompute.ai/compute/clusters/{client_id}[/cyan]

        [bold]Deployment Summary:[/bold]
        • Instance name: [cyan]{instance_name}[/cyan]
        • Cluster name: [cyan]{cluster_name}[/cyan]
        • Deployment ID: [cyan]{deployment.id}[/cyan]
        • Environment: [cyan]Multipass VM[/cyan]
        • Status: [green]Active[/green]

        [bold]Multipass VM Access:[/bold]
        • Open shell in VM: [cyan]multipass shell {instance_name}[/cyan]
        • Execute command: [cyan]multipass exec {instance_name} -- <command>[/cyan]
        • View VM info: [cyan]multipass info {instance_name}[/cyan]
        • VM status: [cyan]multipass list[/cyan]

        [bold]SLURM Cluster Access:[/bold]
        • SSH to VM: [cyan]multipass shell {instance_name}[/cyan]
        • Check SLURM status: [cyan]multipass exec {instance_name} -- sinfo[/cyan]
        • View compute nodes: [cyan]multipass exec {instance_name} -- scontrol show nodes[/cyan]
        • Check job queue: [cyan]multipass exec {instance_name} -- squeue[/cyan]

        [bold]File Transfer:[/bold]
        • Copy to VM: [cyan]multipass transfer <local-file> {instance_name}:<remote-path>[/cyan]
        • Copy from VM: [cyan]multipass transfer {instance_name}:<remote-path> <local-file>[/cyan]
        • Shared directory: [cyan]~/multipass-singlenode/shared[/cyan] (mounted at [cyan]/shared[/cyan] in VM)

        [bold]SLURM Job Management:[/bold]
        • Submit test job: [cyan]multipass exec {instance_name} -- sbatch /path/to/script.sh[/cyan]
        • Interactive session: [cyan]multipass exec {instance_name} -- srun --pty bash[/cyan]
        • Cancel job: [cyan]multipass exec {instance_name} -- scancel <job-id>[/cyan]
        • Job history: [cyan]multipass exec {instance_name} -- sacct[/cyan]

        [bold]VM Management:[/bold]
        • Stop VM: [cyan]multipass stop {instance_name}[/cyan]
        • Start VM: [cyan]multipass start {instance_name}[/cyan]
        • Restart VM: [cyan]multipass restart {instance_name}[/cyan]
        • View VM logs: [cyan]multipass info {instance_name} --format yaml[/cyan]

        [bold]Monitoring & Logs:[/bold]
        • VM resource usage: [cyan]multipass info {instance_name}[/cyan]
        • System logs: [cyan]multipass exec {instance_name} -- journalctl -xe[/cyan]
        • SLURM logs: [cyan]multipass exec {instance_name} -- journalctl -u slurmd -u slurmctld[/cyan]

        [bold]Cleanup:[/bold]
        • Remove deployment: [cyan]vantage app deployment slurm-multipass-localhost remove {instance_name}[/cyan]
        • Manual VM deletion: [cyan]multipass delete {instance_name} --purge[/cyan]

        [yellow]Note:[/yellow] The VM is now running with SLURM configured. Use 'multipass shell {instance_name}' to access the environment.
        [yellow]Tip:[/yellow] Files in ~/multipass-singlenode/shared are automatically synced to /shared in the VM.
        """
    )


def success_destroy_message(deployment: Deployment) -> str:
    return dedent(
        f"""\
        ✅ [bold green]SLURM Multipass Singlenode HPC cleanup completed successfully![/bold green]

        The Juju model '{deployment.cluster.client_id}-model' has been destroyed and all resources have been cleaned up.

        [bold]Next Steps:[/bold]
        • Verify removal: [cyan]multipass list[/cyan]
        • Verify removal: [cyan]vantage app deployments[/cyan]
        • Deploy new cluster: [cyan]vantage cluster create mynewccluster --app slurm-juju-localhost --cloud localhost[/cyan]
        """
    )
