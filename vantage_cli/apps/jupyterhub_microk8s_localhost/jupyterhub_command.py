"""JupyterHub Integration Command for Vantage CLI.

T        # Check if MicroK8s is running
        try:
            result = subprocess.run(
                ["microk8s", "status", "--wait-ready", "--timeout", "30"],
                capture_output=True,
                text=True,
                timeout=35
            )
            if result.returncode != 0:
                self._log_error("MicroK8s is not ready or not running")
                return False
        except subprocess.TimeoutExpired:
            self._log_error("MicroK8s status check timed out")
            return False

        # Check if helm3 addon is enabled
        try:
            result = subprocess.run(
                ["microk8s", "helm", "version"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                self._log_error("MicroK8s helm3 addon is not enabled. Run: microk8s enable helm3")
                return False
        except Exception:
            self._log_error("MicroK8s helm3 addon is not enabled. Run: microk8s enable helm3")
            return Falsevides commands for deploying and managing JupyterHub with Slurm integration
in MicroK8s environments. It creates multi-container pods that combine Jupyter notebook
servers with Slurm login services for seamless HPC integration.
"""

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
import yaml
from rich.console import Console


class JupyterHubManager:
    """Manager for JupyterHub with Slurm integration deployment."""

    def __init__(self):
        self.deployment_script_path = Path(__file__).parent / "deploy_jupyterhub.sh"
        self.console = Console()

    def _log_info(self, message: str):
        """Log info message."""
        self.console.print(f"[blue][INFO][/blue] {message}")

    def _log_success(self, message: str):
        """Log success message."""
        self.console.print(f"[green][SUCCESS][/green] {message}")

    def _log_warning(self, message: str):
        """Log warning message."""
        self.console.print(f"[yellow][WARNING][/yellow] {message}")

    def _log_error(self, message: str):
        """Log error message."""
        self.console.print(f"[red][ERROR][/red] {message}")

    def _check_prerequisites(self) -> bool:
        """Check if required tools are available."""
        required_tools = ["microk8s", "docker"]
        missing_tools: List[str] = []

        for tool in required_tools:
            if subprocess.run(["which", tool], capture_output=True).returncode != 0:
                missing_tools.append(tool)

        if missing_tools:
            self._log_error(f"Missing required tools: {', '.join(missing_tools)}")
            return False

        # Check if MicroK8s is running
        try:
            result = subprocess.run(
                ["microk8s", "status", "--wait-ready", "--timeout", "10"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode != 0:
                self._log_error("MicroK8s is not ready")
                return False
        except subprocess.TimeoutExpired:
            self._log_error("MicroK8s status check timed out")
            return False

        return True

    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate JupyterHub configuration."""
        required_fields = ["namespace", "release_name", "jupyterhub_version"]

        for field in required_fields:
            if field not in config:
                self._log_error(f"Missing required configuration field: {field}")
                return False

        # Validate images
        if "images" in config:
            images = config["images"]
            if "slurm_image" in images and not images["slurm_image"]:
                self._log_error("Slurm image cannot be empty")
                return False

        return True

    def deploy(
        self,
        namespace: str = "jupyterhub",
        release_name: str = "jupyterhub-slurm",
        config_file: Optional[str] = None,
        dry_run: bool = False,
    ) -> bool:
        """Deploy JupyterHub with Slurm integration."""
        self._log_info("Starting JupyterHub with Slurm integration deployment...")

        # Check prerequisites
        if not self._check_prerequisites():
            return False

        # Load configuration
        config = {
            "namespace": namespace,
            "release_name": release_name,
            "jupyterhub_version": "3.3.7",
        }

        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, "r") as f:
                    user_config = yaml.safe_load(f)
                    config.update(user_config)
            except Exception as e:
                self._log_error(f"Failed to load configuration file: {e}")
                return False

        # Validate configuration
        if not self._validate_config(config):
            return False

        if dry_run:
            self._log_info("Dry run mode - would deploy with configuration:")
            self.console.print_json(data=config)
            return True

        try:
            # Prepare environment variables for the deployment script
            env = os.environ.copy()
            env.update(
                {
                    "NAMESPACE": config["namespace"],
                    "RELEASE_NAME": config["release_name"],
                    "JUPYTERHUB_VERSION": config.get("jupyterhub_version", "3.3.7"),
                }
            )

            # Add image configuration if provided
            if "images" in config:
                try:
                    images = config["images"]
                    if isinstance(images, dict):
                        slurm_image = images.get("slurm_image")
                        if slurm_image:
                            env["SLURM_IMAGE"] = slurm_image
                        slurm_login_image = images.get("slurm_login_image")
                        if slurm_login_image:
                            env["SLURM_LOGIN_IMAGE"] = slurm_login_image
                except (KeyError, TypeError):
                    pass

            # Run the deployment script
            self._log_info("Executing deployment script...")
            result = subprocess.run(
                ["bash", str(self.deployment_script_path)],
                env=env,
                capture_output=False,
                text=True,
            )

            if result.returncode == 0:
                self._log_success("JupyterHub with Slurm integration deployed successfully!")
                self.show_access_info(config["namespace"])
                return True
            else:
                self._log_error("Deployment failed")
                return False

        except Exception as e:
            self._log_error(f"Deployment error: {e}")
            return False

    def show_access_info(self, namespace: str):
        """Show access information for the deployed JupyterHub."""
        try:
            # Get service information
            result = subprocess.run(
                [
                    "microk8s",
                    "kubectl",
                    "get",
                    "svc",
                    "proxy-public",
                    "-n",
                    namespace,
                    "-o",
                    "yaml",
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                service = yaml.safe_load(result.stdout)

                # Try to get LoadBalancer IP
                ingress = service.get("status", {}).get("loadBalancer", {}).get("ingress", [])
                if ingress:
                    ip = ingress[0].get("ip")
                    port = service["spec"]["ports"][0]["port"]
                    self._log_success(f"JupyterHub is accessible at: http://{ip}:{port}")
                else:
                    # Fall back to NodePort
                    result = subprocess.run(
                        [
                            "microk8s",
                            "kubectl",
                            "get",
                            "nodes",
                            "-o",
                            "jsonpath='{.items[0].status.addresses[?(@.type==\"InternalIP\")].address}'",
                        ],
                        capture_output=True,
                        text=True,
                    )

                    if result.returncode == 0:
                        ip = result.stdout.strip().strip("'")
                        port = service["spec"]["ports"][0].get("nodePort")
                        if port:
                            self._log_info(f"JupyterHub is accessible at: http://{ip}:{port}")

                self._log_info("Default credentials:")
                self._log_info("  Username: admin (or any username with DummyAuthenticator)")
                self._log_info("  Password: password")

        except Exception as e:
            self._log_warning(f"Could not retrieve access information: {e}")

    def status(self, namespace: str = "jupyterhub") -> bool:
        """Check the status of JupyterHub deployment."""
        try:
            # Check if namespace exists
            result = subprocess.run(
                ["microk8s", "kubectl", "get", "namespace", namespace],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                self._log_warning(f"Namespace '{namespace}' does not exist")
                return False

            # Get pod status
            result = subprocess.run(
                ["microk8s", "kubectl", "get", "pods", "-n", namespace],
                capture_output=False,
                text=True,
            )

            # Get service status
            self._log_info("\nServices:")
            subprocess.run(
                ["microk8s", "kubectl", "get", "svc", "-n", namespace],
                capture_output=False,
                text=True,
            )

            return True

        except Exception as e:
            self._log_error(f"Failed to get status: {e}")
            return False

    def remove(
        self, namespace: str = "jupyterhub", release_name: str = "jupyterhub-slurm"
    ) -> bool:
        """Remove JupyterHub deployment."""
        try:
            self._log_info(
                f"Removing JupyterHub deployment '{release_name}' from namespace '{namespace}'..."
            )

            # Remove Helm release
            result = subprocess.run(
                ["microk8s", "helm", "uninstall", release_name, "-n", namespace],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                self._log_success("Helm release removed successfully")
            else:
                self._log_warning(f"Failed to remove Helm release: {result.stderr}")

            # Remove namespace if empty
            result = subprocess.run(
                ["microk8s", "kubectl", "delete", "namespace", namespace],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                self._log_success(f"Namespace '{namespace}' removed successfully")
            else:
                self._log_warning(f"Failed to remove namespace: {result.stderr}")

            return True

        except Exception as e:
            self._log_error(f"Failed to remove deployment: {e}")
            return False


# Create the JupyterHub app
jupyterhub_app = typer.Typer(
    name="jupyterhub", help="JupyterHub with Slurm integration commands", no_args_is_help=True
)


@jupyterhub_app.command()
def deploy(
    namespace: str = typer.Option("jupyterhub", help="Kubernetes namespace"),
    release_name: str = typer.Option("jupyterhub-slurm", help="Helm release name"),
    config_file: Optional[str] = typer.Option(None, help="Configuration file path"),
    dry_run: bool = typer.Option(
        False, help="Show what would be deployed without actually deploying"
    ),
):
    """Deploy JupyterHub with Slurm integration."""
    manager = JupyterHubManager()
    success = manager.deploy(namespace, release_name, config_file, dry_run)
    if not success:
        raise typer.Exit(code=1)


@jupyterhub_app.command()
def status(namespace: str = typer.Option("jupyterhub", help="Kubernetes namespace")):
    """Check JupyterHub deployment status."""
    manager = JupyterHubManager()
    success = manager.status(namespace)
    if not success:
        raise typer.Exit(code=1)


@jupyterhub_app.command()
def remove(
    namespace: str = typer.Option("jupyterhub", help="Kubernetes namespace"),
    release_name: str = typer.Option("jupyterhub-slurm", help="Helm release name"),
    force: bool = typer.Option(False, help="Force removal without confirmation"),
):
    """Remove JupyterHub deployment."""
    if not force:
        confirm = typer.confirm("Are you sure you want to remove the JupyterHub deployment?")
        if not confirm:
            raise typer.Abort()

    manager = JupyterHubManager()
    success = manager.remove(namespace, release_name)
    if not success:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    jupyterhub_app()
