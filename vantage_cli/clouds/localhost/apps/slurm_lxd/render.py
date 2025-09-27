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
"""Rendering functions for SLURM LXD localhost deployments."""

from textwrap import dedent

from vantage_cli.sdk.deployment.schema import Deployment

__all__ = []


def success_create_message(deployment: Deployment) -> str:
    return dedent(
        f"""\
        🎉 [bold green]Charmed HPC Juju deployment completed successfully![/bold green]

        Access your cluster in the Vantage UI: [cyan]https://app.vantagecompute.ai/compute/clusters/{deployment.cluster.client_id}[/cyan]

        [bold]Deployment Summary:[/bold]
        • Juju controller: [cyan]{deployment.cluster.name}-controller[/cyan]
        • Juju model: [cyan]{deployment.cluster.name}-model[/cyan]
        • Deployment ID: [cyan]{deployment.id}[/cyan]
        • Container environment: [cyan]LXD containers[/cyan]

        [bold]Connect to Charmed HPC Cluster:[/bold]
        • SLURM controller: [cyan]juju ssh slurmctld/0[/cyan]
        • SLURM compute node: [cyan]juju ssh slurmd/0[/cyan]
        • JupyterHub interface: [cyan]juju ssh jupyterhub/0[/cyan]

        [bold]Access Web Interfaces:[/bold]
        • Get JupyterHub URL: [cyan]juju status jupyterhub --format=json | jq -r '.applications.jupyterhub.units | to_entries[0].value["public-address"]'[/cyan]
        • JupyterHub access: [cyan]http://<jupyterhub-ip>:8000[/cyan]
        • SLURM job submission: Available via JupyterHub terminal or SSH to slurmctld

        [bold]Monitoring & Management:[/bold]
        • Check all services: [cyan]juju status[/cyan]
        • Monitor deployment: [cyan]juju status --watch 5s[/cyan]
        • View application logs: [cyan]juju debug-log[/cyan]
        • Monitor SLURM controller: [cyan]juju debug-log --include=slurmctld/0[/cyan]
        • Monitor compute nodes: [cyan]juju debug-log --include=slurmd[/cyan]
        • Check JupyterHub logs: [cyan]juju debug-log --include=jupyterhub/0[/cyan]

        [bold]SLURM Job Management:[/bold]
        • Submit test job: [cyan]juju ssh slurmctld/0 -- sinfo[/cyan]
        • Check queue: [cyan]juju ssh slurmctld/0 -- squeue[/cyan]
        • Node status: [cyan]juju ssh slurmctld/0 -- scontrol show nodes[/cyan]

        [bold]Other Useful Commands:[/bold]
        • Check cluster status: [cyan]vantage deployment slurm-juju-localhost status[/cyan]
        • Scale compute nodes: [cyan]juju add-unit slurmd[/cyan]
        • Remove deployment: [cyan]vantage deployment slurm-juju-localhost remove[/cyan]
        • Access Juju GUI: [cyan]juju gui[/cyan]

        [yellow]Note:[/yellow] Use 'juju status' to monitor deployment progress. All services run in LXD containers.
        """
    )


def success_destroy_message(deployment: Deployment) -> str:
    return dedent(
        f"""\
        ✅ [bold green]Charmed HPC cleanup completed successfully![/bold green]

        The Juju model '{deployment.cluster.name}-model' has been destroyed and all resources have been cleaned up.

        [bold]Next Steps:[/bold]
        • Verify removal: [cyan]juju models[/cyan]
        • Check controller status: [cyan]juju controllers[/cyan]
        • Deploy new cluster: [cyan]vantage deployment slurm-juju-localhost deploy <cluster-name>[/cyan]
        """
    )
