"""Rendering functions for JupyterHub MicroK8s localhost app.

This module provides functions to format success and failure content
for JupyterHub deployment operations.
"""

from typing import Any


def format_deployment_success_content(namespace: str, release_name: str, **kwargs: Any) -> str:
    """Format the success content for JupyterHub deployment completion.

    Args:
        namespace: Kubernetes namespace where JupyterHub was deployed
        release_name: Helm release name used for deployment
        **kwargs: Additional arguments (unused but kept for consistency)

    Returns:
        Formatted rich text content for successful deployment
    """
    return f"""🎉 [bold green]JupyterHub deployment completed successfully![/bold green]

[bold]Deployment Summary:[/bold]
• JupyterHub namespace: [cyan]{namespace}[/cyan]
• Release name: [cyan]{release_name}[/cyan]
• Chart source: [cyan]JupyterHub official Helm chart[/cyan]
• Authentication: [cyan]Dummy authenticator (development mode)[/cyan]

[bold]🚀 Getting Started[/bold]
1. Port-forward JupyterHub service:
   [cyan]microk8s kubectl port-forward --address 0.0.0.0 -n {namespace} service/{release_name}-hub 8000:8000[/cyan]

2. Access JupyterHub in your browser:
   [cyan]http://localhost:8000[/cyan]

3. Login with development credentials:
   • Username: [cyan]admin[/cyan] (or any username)
   • Password: [cyan]admin[/cyan]

[bold]📊 Status & Monitoring[/bold]
• Check deployment status:
  [cyan]vantage deployment jupyterhub-microk8s-localhost status --namespace {namespace}[/cyan]

• View pod status:
  [cyan]microk8s kubectl get pods -n {namespace}[/cyan]

• Check hub logs:
  [cyan]microk8s kubectl logs -n {namespace} -l app.kubernetes.io/name=jupyterhub,app.kubernetes.io/component=hub[/cyan]

[bold]🔧 Management Commands[/bold]
• Scale hub deployment:
  [cyan]microk8s kubectl scale deployment -n {namespace} {release_name}-hub --replicas=2[/cyan]

• Access hub shell:
  [cyan]microk8s kubectl exec -it -n {namespace} deployment/{release_name}-hub -- bash[/cyan]

• Update deployment:
  [cyan]microk8s helm upgrade {release_name} jupyterhub/jupyterhub -n {namespace}[/cyan]

• Remove deployment:
  [cyan]vantage deployment jupyterhub-microk8s-localhost remove --namespace {namespace}[/cyan]

[bold]🌐 External Access[/bold]
• Get external IP (if LoadBalancer available):
  [cyan]microk8s kubectl get services -n {namespace} {release_name}-hub -o jsonpath='{{.status.loadBalancer.ingress[0].ip}}'[/cyan]

• External access URL: [cyan]http://<external-ip>:8000[/cyan]

[bold]👥 User Management[/bold]
• List active user servers:
  [cyan]microk8s kubectl get pods -n {namespace} -l app.kubernetes.io/component=singleuser-server[/cyan]

• View user server events:
  [cyan]microk8s kubectl get events -n {namespace} --sort-by='.lastTimestamp'[/cyan]

[bold]⚡ Services Overview[/bold]
• Hub service: [cyan]{release_name}-hub[/cyan]
• Proxy service: [cyan]{release_name}-proxy-public[/cyan]
• User servers: [cyan]Dynamic spawn via Kubernetes[/cyan]

[yellow]💡 Development Note:[/yellow] JupyterHub is configured with dummy authentication for development.
[yellow]🔒 Production Warning:[/yellow] Configure proper authentication (OAuth, LDAP, etc.) for production use."""


def format_deployment_failure_content(error_message: str, **kwargs: Any) -> str:
    """Format the failure content for JupyterHub deployment errors.

    Args:
        error_message: The error message describing what went wrong
        **kwargs: Additional arguments (unused but kept for consistency)

    Returns:
        Formatted rich text content for deployment failure
    """
    return f"""❌ [bold red]JupyterHub deployment failed[/bold red]

[bold]Error Details:[/bold]
{error_message}

[bold]🔍 Troubleshooting Steps[/bold]

[bold]1. Check Prerequisites:[/bold]
• Verify MicroK8s is running:
  [cyan]microk8s status --wait-ready[/cyan]

• Ensure required addons are enabled:
  [cyan]microk8s enable dns helm3 storage[/cyan]

• Check MicroK8s node status:
  [cyan]microk8s kubectl get nodes[/cyan]

[bold]2. Check Resources:[/bold]
• View available resources:
  [cyan]microk8s kubectl top nodes[/cyan]

• Check disk space:
  [cyan]df -h[/cyan]

• Memory usage:
  [cyan]free -h[/cyan]

[bold]3. Namespace & Deployment Issues:[/bold]
• List namespaces:
  [cyan]microk8s kubectl get namespaces[/cyan]

• Check events in target namespace:
  [cyan]microk8s kubectl get events -n jupyterhub --sort-by='.lastTimestamp'[/cyan]

• View failed pods:
  [cyan]microk8s kubectl get pods -n jupyterhub --field-selector=status.phase=Failed[/cyan]

[bold]4. Helm Issues:[/bold]
• List Helm releases:
  [cyan]microk8s helm list -A[/cyan]

• Check Helm repositories:
  [cyan]microk8s helm repo list[/cyan]

• Update repositories:
  [cyan]microk8s helm repo update[/cyan]

[bold]5. Network & Connectivity:[/bold]
• Check CoreDNS pods:
  [cyan]microk8s kubectl get pods -n kube-system -l k8s-app=kube-dns[/cyan]

• Test internal DNS:
  [cyan]microk8s kubectl run test-dns --image=busybox --rm -it -- nslookup kubernetes.default[/cyan]

[bold]🔄 Recovery Options[/bold]
• Retry deployment:
  [cyan]vantage deployment jupyterhub-microk8s-localhost deploy[/cyan]

• Clean up failed resources:
  [cyan]microk8s kubectl delete namespace jupyterhub[/cyan]

• Reset MicroK8s (if needed):
  [cyan]microk8s reset[/cyan]

[bold]📞 Need Help?[/bold]
• Check deployment logs: [cyan]vantage deployment logs[/cyan]
• Contact support: [cyan]vantage contact support[/cyan]
• View documentation: [cyan]vantage docs[/cyan]"""
