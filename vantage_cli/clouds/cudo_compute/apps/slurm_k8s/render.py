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
"""Rendering functions for SLURM on K8S Cudo Compute deployments."""

from textwrap import dedent

from vantage_cli.sdk.deployment.schema import Deployment

__all__ = []


def success_create_message(deployment: Deployment) -> str:
    return dedent(
        f"""\
        🎉 [bold green]Cudo Compute Slurm on K8S![/bold green]

        Access your cluster in the Vantage UI: [cyan]https://app.vantagecompute.ai/compute/clusters/{deployment.cluster.client_id}[/cyan]

        [bold]Deployment Summary:[/bold]

        [bold]Connect to your Cudo Compute Cluster:[/bold]

        [bold]Monitoring & Management:[/bold]

        [bold]SLURM Job Management:[/bold]

        [bold]Other Useful Commands:[/bold]

        [yellow]Note:[/yellow] Use blah blah blah.
        """
    )


def success_destroy_message(deployment: Deployment) -> str:
    return dedent(
        """\
        ✅ [bold green]Cudo Compute SLURM on K8S cleanup completed successfully![/bold green]

        [bold]Next Steps:[/bold]
        """
    )
