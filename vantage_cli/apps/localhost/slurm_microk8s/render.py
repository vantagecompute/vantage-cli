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

from textwrap import dedent

from rich.console import Console
from rich.panel import Panel

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


def show_getting_started_help(console: Console) -> None:
    """Show getting started help after successful MicroK8s SLURM deployment.

    Displays connection instructions and useful commands for accessing the deployed cluster.
    """
    help_message = dedent(
        """
        🎉 SLURM cluster deployment completed successfully!

        📋 Next Steps:

        1️⃣ Check cluster status:
           microk8s.kubectl get pods -A --namespace slurm

        2️⃣ Get SLURM login service connection details:
           SLURM_LOGIN_IP="$(microk8s.kubectl get services -n slurm slurm-login-slinky -o jsonpath='{.status.loadBalancer.ingress[0].ip}')"
           SLURM_LOGIN_PORT="$(microk8s.kubectl get services -n slurm slurm-login-slinky -o jsonpath='{.spec.ports[0].port}')"

        3️⃣ Connect to SLURM login node:
           # Using root access (if rootSshAuthorizedKeys was configured):
           ssh -p ${SLURM_LOGIN_PORT:-22} root@${SLURM_LOGIN_IP}

           # Using SSSD user authentication (if SSSD is configured):
           ssh -p ${SLURM_LOGIN_PORT:-22} ${USER}@${SLURM_LOGIN_IP}

        4️⃣ Useful SLURM commands once connected:
           sinfo                    # Show cluster information
           squeue                   # Show job queue
           srun hostname            # Run simple test job
           sbatch <script.sh>       # Submit batch job

        📚 Additional Resources:
           • MicroK8s docs: https://microk8s.io/docs
           • SLURM docs: https://slurm.schedmd.com/documentation.html
           • Troubleshooting: microk8s.kubectl logs -n slurm <pod-name>
        """
    ).strip()

    console.print(
        Panel(
            help_message,
            title="🚀 Getting Started with Your SLURM Cluster",
            title_align="left",
            border_style="green",
            padding=(1, 2),
        )
    )
