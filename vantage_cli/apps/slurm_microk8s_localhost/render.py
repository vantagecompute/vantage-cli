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
"""Rendering functions for SLURM MicroK8s localhost deployment."""

from .constants import (
    DEFAULT_NAMESPACE_CERT_MANAGER,
    DEFAULT_NAMESPACE_PROMETHEUS,
    DEFAULT_NAMESPACE_SLINKY,
    DEFAULT_NAMESPACE_SLURM,
)


def format_deployment_success_content(client_id: str) -> str:
    """Format the success message content for SLURM deployment.

    Args:
        client_id: The client ID for accessing the Vantage UI

    Returns:
        Formatted success message string
    """
    return f"""🎉 [bold green]SLURM MicroK8s deployment completed successfully![/bold green]

Access your cluster in the Vantage UI: [cyan]https://app.vantagecompute.ai/compute/clusters/{client_id}[/cyan]

[bold]Deployment Summary:[/bold]
• SLURM operator namespace: [cyan]{DEFAULT_NAMESPACE_SLINKY}[/cyan]
• SLURM cluster namespace: [cyan]{DEFAULT_NAMESPACE_SLURM}[/cyan]
• Prometheus namespace: [cyan]{DEFAULT_NAMESPACE_PROMETHEUS}[/cyan]
• Cert Manager namespace: [cyan]{DEFAULT_NAMESPACE_CERT_MANAGER}[/cyan]

[bold]Connect to SLURM Cluster:[/bold]
• Get connection details:
  [cyan]SLURM_LOGIN_IP="$(microk8s kubectl get services -n {DEFAULT_NAMESPACE_SLURM} slurm-login-slinky -o jsonpath='{{.status.loadBalancer.ingress[0].ip}}')"[/cyan]
  [cyan]SLURM_LOGIN_PORT="$(microk8s kubectl get services -n {DEFAULT_NAMESPACE_SLURM} slurm-login-slinky -o jsonpath='{{.spec.ports[0].port}}')"[/cyan]

• Connect via SSH:
  [cyan]ssh -p ${{SLURM_LOGIN_PORT:-22}} ${{USER}}@${{SLURM_LOGIN_IP}}[/cyan]

[bold]Other Useful Commands:[/bold]
• Check pod status: [cyan]microk8s kubectl get pods -A --namespace {DEFAULT_NAMESPACE_SLURM}[/cyan]
• View cluster status: [cyan]vantage deployment slurm-microk8s-localhost status[/cyan]
• Access logs: [cyan]microk8s kubectl logs -n {DEFAULT_NAMESPACE_SLURM} <pod-name>[/cyan]
• Connect to pod directly: [cyan]microk8s kubectl exec -it -n {DEFAULT_NAMESPACE_SLURM} <pod-name> -- /bin/bash[/cyan]
• Remove deployment: [cyan]vantage deployment slurm-microk8s-localhost remove[/cyan]"""


def format_deployment_failure_content(error_message: str) -> str:
    """Format the failure message content for SLURM deployment.

    Args:
        error_message: The error message to display

    Returns:
        Formatted failure message string
    """
    return f"""❌ [bold red]SLURM MicroK8s deployment failed[/bold red]

[bold]Error:[/bold] {error_message}

[bold]Troubleshooting Tips:[/bold]
• Ensure MicroK8s is installed and running: [cyan]microk8s status[/cyan]
• Check if required addons are enabled: [cyan]microk8s status[/cyan]
• Enable required addons:
  [cyan]microk8s enable dns hostpath-storage metallb helm3 cert-manager[/cyan]
• Check system resources: [cyan]df -h && free -h[/cyan]
• View deployment logs: [cyan]vantage deployment slurm-microk8s-localhost status[/cyan]

[bold]Get Help:[/bold]
• Documentation: [cyan]https://docs.vantagecompute.ai[/cyan]
• Support: [cyan]https://support.vantagecompute.ai[/cyan]"""
