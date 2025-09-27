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
"""Deployment App CRUD SDK for discovering and filtering deployment applications."""

import importlib
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

from vantage_cli.constants import VANTAGE_CLI_DEV_APPS_DIR
from vantage_cli.sdk.deployment_app.schema import DeploymentApp

logger = logging.getLogger(__name__)


class DeploymentAppSDK:
    """SDK for managing deployment app discovery and filtering."""

    def __init__(self):
        """Initialize the Deployment App SDK and discover available apps."""
        self._app_registry: Dict[str, DeploymentApp] = {}
        self._discover_apps()

    def list(
        self,
        cloud: Optional[str] = None,
        substrate: Optional[str] = None,
    ) -> List[DeploymentApp]:
        """List deployment apps with optional filtering.

        Args:
            cloud: Optional cloud filter (e.g., 'localhost', 'cudo-compute')
            substrate: Optional substrate filter (e.g., 'lxd', 'metal', 'k8s')

        Returns:
            List of DeploymentApp instances matching the filters
        """
        apps = list(self._app_registry.values())

        # Filter by cloud if specified
        if cloud:
            apps = [app for app in apps if app.cloud == cloud]
            logger.debug(f"Filtered apps by cloud '{cloud}': {[a.name for a in apps]}")

        # Filter by substrate if specified
        if substrate:
            apps = [app for app in apps if app.substrate == substrate]
            logger.debug(f"Filtered apps by substrate '{substrate}': {[a.name for a in apps]}")

        return apps

    def get(self, name: str) -> Optional[DeploymentApp]:
        """Get a specific deployment app by name.

        Args:
            name: The app name (e.g., 'slurm-lxd')

        Returns:
            DeploymentApp instance or None if not found
        """
        return self._app_registry.get(name)

    def get_all_clouds(self) -> List[str]:
        """Get a list of all unique clouds across all apps.

        Returns:
            Sorted list of unique cloud names
        """
        clouds: set[str] = set()
        for app in self._app_registry.values():
            clouds.add(app.cloud)
        return sorted(clouds)

    def get_all_substrates(self) -> List[str]:
        """Get a list of all unique substrates across all apps.

        Returns:
            Sorted list of unique substrate names
        """
        substrates = {app.substrate for app in self._app_registry.values()}
        return sorted(substrates)

    def refresh(self) -> None:
        """Force refresh the app registry by rediscovering apps from the filesystem."""
        self._app_registry.clear()
        self._discover_apps()

    # Private methods for app discovery (integrated from apps/utils.py)

    def _discover_apps(self) -> None:
        """Discover all available deployment apps from the filesystem."""
        clouds_dir = Path(__file__).parent.parent.parent / "clouds"

        if not clouds_dir.exists():
            logger.warning(f"Clouds directory not found: {clouds_dir}")
            return

        # Discover built-in and dev apps
        built_in_apps = self._discover_builtin_apps(clouds_dir)
        dev_apps = self._discover_dev_apps()

        # Combine and process all apps
        all_apps = built_in_apps + dev_apps
        for app_path, is_builtin in all_apps:
            self._process_app(app_path, is_builtin)

        logger.debug(f"Discovered {len(self._app_registry)} deployment apps")

    def _discover_builtin_apps(self, clouds_dir: Path) -> List[tuple[Path, bool]]:
        """Discover built-in apps from the clouds directory structure.

        Looks for apps in: vantage_cli/clouds/{cloud}/apps/{app_name}/
        """
        built_in_apps = []

        # Iterate through each cloud provider directory
        for cloud_dir in clouds_dir.iterdir():
            if not cloud_dir.is_dir() or cloud_dir.name.startswith("__"):
                continue

            # Look for apps directory within the cloud directory
            apps_dir = cloud_dir / "apps"
            if not apps_dir.exists() or not apps_dir.is_dir():
                continue

            # Iterate through app directories
            for app_path in apps_dir.iterdir():
                if app_path.is_dir() and not app_path.name.startswith("__"):
                    app_module_path = app_path / "app.py"
                    if app_module_path.exists():
                        built_in_apps.append((app_path, True))  # (path, is_builtin)
                        logger.debug(f"Found app: {cloud_dir.name}/{app_path.name}")

        return built_in_apps

    def _discover_dev_apps(self) -> List[tuple[Path, bool]]:
        """Discover dev apps from the dev apps directory."""
        dev_apps = []
        if VANTAGE_CLI_DEV_APPS_DIR.exists():
            dev_apps_dir = VANTAGE_CLI_DEV_APPS_DIR / "apps"
            if dev_apps_dir.exists():
                # Add dev apps directory to Python path
                dev_apps_parent = str(VANTAGE_CLI_DEV_APPS_DIR)
                if dev_apps_parent not in sys.path:
                    sys.path.insert(0, dev_apps_parent)

                # Sort dev apps to load keycloak before full (dependency order)
                app_paths = []
                for app_path in dev_apps_dir.iterdir():
                    if app_path.is_dir() and not (
                        app_path.name.startswith("__") or app_path.name.startswith(".")
                    ):
                        app_module_path = app_path / "app.py"
                        if app_module_path.exists():
                            app_paths.append(app_path)

                # Sort so keycloak comes before full
                app_paths.sort(key=lambda p: (0 if "keycloak" in p.name else 1, p.name))

                for app_path in app_paths:
                    dev_apps.append((app_path, False))  # (path, is_builtin)
        return dev_apps

    def _process_app(self, app_path: Path, is_builtin: bool) -> None:
        """Process a single app and add it to the registry."""
        app_name = app_path.name

        try:
            # Load the app module and check if it has a create function
            app_module = self._load_app_module(app_path, app_name, is_builtin)
            if app_module is None or not hasattr(app_module, "create"):
                return

            constants_module = self._load_constants_module(app_path, app_name, is_builtin)

            # Extract app name, cloud and substrate from constants module
            if constants_module and hasattr(constants_module, "APP_NAME"):
                command_name = constants_module.APP_NAME
            else:
                # Fallback to directory name with underscores replaced by hyphens
                command_name = app_name.replace("_", "-")

            cloud = (
                constants_module.CLOUD
                if constants_module and hasattr(constants_module, "CLOUD")
                else "localhost"
            )
            substrate = (
                constants_module.SUBSTRATE
                if constants_module and hasattr(constants_module, "SUBSTRATE")
                else "unknown"
            )

            # Create DeploymentApp instance with module reference
            deployment_app = DeploymentApp(
                name=command_name,
                cloud=cloud,
                substrate=substrate,
                module=app_module,
            )

            # Add to registry
            self._app_registry[command_name] = deployment_app
            logger.debug(
                f"Registered app '{command_name}' - cloud: {cloud}, substrate: {substrate}"
            )

        except Exception as e:
            logger.debug(f"Failed to process app {app_name}: {e}")

    def _load_app_module(self, app_path: Path, app_name: str, is_builtin: bool):
        """Load the app module.

        Args:
            app_path: Path to the app directory
            app_name: Name of the app directory
            is_builtin: Whether this is a built-in app

        Returns:
            The loaded module or None if loading failed
        """
        try:
            if is_builtin:
                # Import built-in app - handle nested structure
                parent_dir = app_path.parent
                cloud_dir = app_path.parent.parent

                if parent_dir.name == "apps" and cloud_dir.name in ["localhost", "cudo_compute"]:
                    # Nested app (e.g., clouds/localhost/apps/slurm_lxd)
                    cloud = cloud_dir.name
                    app_module = importlib.import_module(
                        f"vantage_cli.clouds.{cloud}.apps.{app_name}.app"
                    )
                else:
                    # Fallback for top-level apps (if any exist)
                    app_module = importlib.import_module(
                        f"vantage_cli.clouds.localhost.apps.{app_name}.app"
                    )

                return app_module
            else:
                # For dev apps, check if app.py exists but don't import yet
                # (can be enhanced later to support dev app imports)
                app_file = app_path / "app.py"
                if app_file.exists():
                    # TODO: Implement dev app loading
                    return None
                return None

        except Exception as e:
            logger.debug(f"Failed to load module for app {app_name}: {e}")
            return None

    def _load_constants_module(self, app_path: Path, app_name: str, is_builtin: bool):
        """Load the app constants module.

        Args:
            app_path: Path to the app directory
            app_name: Name of the app directory
            is_builtin: Whether this is a built-in app

        Returns:
            The loaded module or None if loading failed
        """
        try:
            if is_builtin:
                # Import built-in app - handle nested structure
                parent_dir = app_path.parent
                cloud_dir = app_path.parent.parent

                if parent_dir.name == "apps" and cloud_dir.name in ["localhost", "cudo_compute"]:
                    # Nested app (e.g., clouds/localhost/apps/slurm_lxd)
                    cloud = cloud_dir.name
                    constants_module = importlib.import_module(
                        f"vantage_cli.clouds.{cloud}.apps.{app_name}.constants"
                    )
                else:
                    # Fallback for top-level apps (if any exist)
                    constants_module = importlib.import_module(
                        f"vantage_cli.clouds.localhost.apps.{app_name}.constants"
                    )
            else:
                # External apps - no constants module
                constants_module = None

            return constants_module
        except Exception as e:
            logger.debug(f"Failed to load constants module for app {app_name}: {e}")
            return None
