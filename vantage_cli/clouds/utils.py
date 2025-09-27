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
"""Utility functions for MicroK8s deployment."""

import importlib
import importlib.util
import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import typer
from rich.console import Console
from rich.table import Table

from vantage_cli.constants import VANTAGE_CLI_DEV_APPS_DIR
from vantage_cli.sdk.cluster.schema import Cluster


class PrerequisiteStatus(Enum):
    """Status of a prerequisite check."""

    AVAILABLE = "available"
    MISSING = "missing"
    ERROR = "error"


@dataclass
class PrerequisiteResult:
    """Result of a prerequisite check."""

    name: str
    status: PrerequisiteStatus
    version: Optional[str] = None
    error_message: Optional[str] = None
    installation_hint: Optional[str] = None


@dataclass
class PrerequisiteCheck:
    """Definition of a prerequisite check."""

    name: str
    command: List[str]
    version_command: Optional[List[str]] = None
    installation_hint: Optional[str] = None
    required: bool = True


def check_prerequisites(
    checks: List[PrerequisiteCheck],
    console: Console,
    verbose: bool = False,
    show_table: bool = True,
) -> Tuple[bool, List[PrerequisiteResult]]:
    """Check multiple prerequisites and report results to the user.

    Args:
        checks: List of prerequisite checks to perform
        console: Console for output
        verbose: Whether to show verbose output
        show_table: Whether to display a results table

    Returns:
        Tuple of (all_requirements_met, list_of_results)
    """
    results = []
    all_required_met = True

    if verbose:
        console.print("[blue]ℹ[/blue] Checking prerequisites...")

    for check in checks:
        result = _check_single_prerequisite(check, verbose, console)
        results.append(result)

        if check.required and result.status != PrerequisiteStatus.AVAILABLE:
            all_required_met = False

    if show_table:
        _display_prerequisite_table(results, console)

    # Show installation hints for missing required tools
    missing_required = [
        r
        for r in results
        if r.status != PrerequisiteStatus.AVAILABLE
        and any(c.required for c in checks if c.name == r.name)
    ]

    if missing_required:
        console.print()
        console.print("[red]⚠ Missing required prerequisites:[/red]")
        for result in missing_required:
            console.print(f"  • {result.name}")
            if result.installation_hint:
                console.print(f"    💡 {result.installation_hint}")
        console.print()

    # Show summary
    if all_required_met:
        if verbose:
            console.print("[green]✓[/green] All required prerequisites are available!")
    else:
        console.print(
            "[red]✗[/red] Some required prerequisites are missing. Please install them before proceeding."
        )

    return all_required_met, results


def _clean_error_message(error_message: str) -> str:
    """Clean up error messages to show concise, readable output."""
    if not error_message:
        return "Command failed"

    # Handle common patterns
    if "not found" in error_message.lower():
        return "Command not found"

    # Handle multiline tracebacks - extract the most relevant line
    lines = error_message.strip().split("\n")
    if len(lines) > 3:  # If it's a long traceback
        # Look for common error patterns
        for line in lines:
            if "LookupError:" in line or "Error:" in line or "Exception:" in line:
                return line.strip()
        # If no specific error found, return a generic message
        return "Command failed with error"

    # For shorter messages, clean up but keep essential info
    cleaned = error_message.strip()
    if len(cleaned) > 100:  # Truncate very long messages
        cleaned = cleaned[:97] + "..."

    return cleaned


def _check_single_prerequisite(
    check: PrerequisiteCheck, verbose: bool, console: Console
) -> PrerequisiteResult:
    """Check a single prerequisite."""
    try:
        # Check if tool is available
        result = subprocess.run(check.command, capture_output=True, text=True, timeout=10)

        if result.returncode != 0:
            cleaned_error = _clean_error_message(result.stderr)
            if verbose:
                console.print(f"[yellow]⚠[/yellow] {check.name}: Command failed - {cleaned_error}")
            return PrerequisiteResult(
                name=check.name,
                status=PrerequisiteStatus.MISSING,
                error_message=cleaned_error,
                installation_hint=check.installation_hint,
            )

        # Get version if version command is provided
        version = None
        if check.version_command:
            try:
                version_result = subprocess.run(
                    check.version_command, capture_output=True, text=True, timeout=5
                )
                if version_result.returncode == 0:
                    version = version_result.stdout.strip().split("\n")[0]  # Take first line
            except Exception:
                pass  # Version check is optional

        if verbose:
            version_str = f" (version: {version})" if version else ""
            console.print(f"[green]✓[/green] {check.name}: Available{version_str}")

        return PrerequisiteResult(
            name=check.name,
            status=PrerequisiteStatus.AVAILABLE,
            version=version,
            installation_hint=check.installation_hint,
        )

    except subprocess.TimeoutExpired:
        if verbose:
            console.print(f"[red]✗[/red] {check.name}: Check timed out")
        return PrerequisiteResult(
            name=check.name,
            status=PrerequisiteStatus.ERROR,
            error_message="Check timed out",
            installation_hint=check.installation_hint,
        )
    except FileNotFoundError:
        if verbose:
            console.print(f"[red]✗[/red] {check.name}: Not found")
        return PrerequisiteResult(
            name=check.name,
            status=PrerequisiteStatus.MISSING,
            error_message="Command not found",
            installation_hint=check.installation_hint,
        )
    except Exception as e:
        cleaned_error = _clean_error_message(str(e))
        if verbose:
            console.print(f"[red]✗[/red] {check.name}: Error - {cleaned_error}")
        return PrerequisiteResult(
            name=check.name,
            status=PrerequisiteStatus.ERROR,
            error_message=cleaned_error,
            installation_hint=check.installation_hint,
        )


def _display_prerequisite_table(results: List[PrerequisiteResult], console: Console) -> None:
    """Display prerequisite check results in a table."""
    table = Table(title="Prerequisite Check Results")
    table.add_column("Tool", style="cyan", no_wrap=True)
    table.add_column("Status", style="bold")
    table.add_column("Version", style="dim")
    table.add_column("Notes", style="dim")

    for result in results:
        if result.status == PrerequisiteStatus.AVAILABLE:
            status = "[green]✓ Available[/green]"
        elif result.status == PrerequisiteStatus.MISSING:
            status = "[red]✗ Missing[/red]"
        else:
            status = "[yellow]⚠ Error[/yellow]"

        version = result.version or "-"
        notes = result.error_message or "-"

        table.add_row(result.name, status, version, notes)

    console.print()
    console.print(table)
    console.print()


async def get_cluster_data(
    ctx: typer.Context, cluster_name: str, dev_run: bool, verbose: bool
) -> Cluster:
    """Get cluster data either from dev mode or actual cluster lookup.

    Args:
        ctx: Typer context
        cluster_name: Name of the cluster
        dev_run: Whether to use dev mode
        verbose: Whether to show verbose output

    Returns:
        Cluster object containing cluster data

    Raises:
        ValueError: If cluster is not found in non-dev mode
    """
    from vantage_cli.clouds.common import generate_dev_cluster_data

    cluster_obj = generate_dev_cluster_data(cluster_name)
    if not dev_run:
        from vantage_cli.sdk.cluster.crud import cluster_sdk

        fetched_cluster = await cluster_sdk.get_cluster_by_name(ctx=ctx, cluster_name=cluster_name)
        if fetched_cluster is None:
            raise ValueError(f"Cluster '{cluster_name}' not found")
        cluster_obj = fetched_cluster
    else:
        if verbose:
            ctx.obj.console.print(
                f"[blue]Using dev run mode with dummy cluster data for '{cluster_name}'[/blue]"
            )
    # Return Cluster object directly
    return cluster_obj


def _load_dev_app_as_package(app_path: Path, app_name: str, cloud: str = "localhost"):
    """Load a dev app as a proper Python package with support for relative imports."""
    import types

    vantage_cli_module_name = f"vantage_cli.clouds.{cloud}.apps.{app_name}"

    # Ensure parent package exists for relative imports
    parent_package = f"vantage_cli.clouds.{cloud}.apps"
    if parent_package not in sys.modules:
        parent_mod = types.ModuleType(parent_package)
        parent_mod.__path__ = []
        parent_mod.__package__ = parent_package
        sys.modules[parent_package] = parent_mod

    # Create the main package module with proper __path__ for relative imports
    package_module = types.ModuleType(vantage_cli_module_name)
    package_module.__path__ = [str(app_path)]  # This enables relative imports
    package_module.__package__ = vantage_cli_module_name
    sys.modules[vantage_cli_module_name] = package_module

    # Load all Python files as submodules
    app_module = None
    app_dir_path = str(app_path)

    for root, _, files in os.walk(app_dir_path):
        for file in files:
            if file.endswith(".py") and file != "__init__.py":
                file_path = os.path.join(root, file)
                module_stem = file[:-3]  # Remove .py extension

                # Create full module name
                module_name = f"{vantage_cli_module_name}.{module_stem}"

                # Create and load the module
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    module.__package__ = (
                        vantage_cli_module_name  # Set package for relative imports
                    )
                    sys.modules[module_name] = module

                    # Set as attribute on package for dot notation access
                    setattr(package_module, module_stem, module)

                    # Execute the module
                    spec.loader.exec_module(module)

                    if file == "app.py":
                        app_module = module

    return app_module


def _discover_builtin_apps(built_in_apps_dir: Path) -> list[tuple]:
    """Discover built-in apps from the apps directory.

    Supports both top-level apps and nested apps (e.g., localhost/slurm_*).
    """
    built_in_apps = []

    for app_path in built_in_apps_dir.iterdir():
        if app_path.is_dir() and not app_path.name.startswith("__"):
            # Check if it's a direct app directory
            app_module_path = app_path / "app.py"
            if app_module_path.exists():
                built_in_apps.append((app_path, True))  # (path, is_builtin)
            # Check if it's a category directory (e.g., localhost/)
            elif app_path.is_dir():
                # Look for nested app directories
                for nested_app_path in app_path.iterdir():
                    if nested_app_path.is_dir() and not nested_app_path.name.startswith("__"):
                        nested_app_module_path = nested_app_path / "app.py"
                        if nested_app_module_path.exists():
                            built_in_apps.append((nested_app_path, True))

    return built_in_apps


def _discover_dev_apps() -> list[tuple]:
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


def _process_app(app_path: Path, is_builtin: bool, apps: Dict[str, Dict[str, Any]]) -> None:
    """Process a single app and add it to the apps dictionary."""
    app_name = app_path.name
    command_name = app_name.replace("_", "-")

    try:
        if is_builtin:
            # Import built-in app - handle nested structure (e.g., localhost/slurm_lxd)
            # Check if this is a nested app (has a parent directory that's not 'apps')
            parent_dir = app_path.parent
            cloud_dir = (
                app_path.parent.parent
            )  # Should be a cloud directory (localhost, cudo_compute, etc.)

            if parent_dir.name == "apps" and cloud_dir.parent.name == "clouds":
                # Nested app (e.g., localhost/apps/slurm_lxd or cudo_compute/apps/slurm_metal)
                cloud_name = cloud_dir.name
                app_module = importlib.import_module(
                    f"vantage_cli.clouds.{cloud_name}.apps.{app_name}.app"
                )
            else:
                # Legacy or incorrectly structured app - skip
                logging.warning(f"App {app_name} has incorrect structure, skipping")
                return
        else:
            # Import dev app using direct file loading with proper package system
            app_module = None
            try:
                app_module = _load_dev_app_as_package(app_path, app_name)
                if app_module is None:
                    return

            except Exception:
                return
    except ImportError:
        return
    except Exception:
        return

    # Check if create function exists
    try:
        has_create = hasattr(app_module, "create")
        if has_create:
            create_function = getattr(app_module, "create")
            # Use command_name (with hyphens) as key so CLI can find it
            apps[command_name] = {
                "module": app_module,
                "create_function": create_function,
            }
    except Exception:
        pass


def get_jupyterhub_token(cluster_data: Dict[str, Any]) -> Optional[str]:
    """Return Jupyterhub Token if exists in cluster_data or None."""
    jupyterhub_token = None
    if "creationParameters" in cluster_data:
        if jupyterhub_token_data := cluster_data["creationParameters"].get("jupyterhub_token"):
            jupyterhub_token = jupyterhub_token_data
    return jupyterhub_token


def get_sssd_binder_password(cluster_data: Dict[str, Any]) -> Optional[str]:
    """Return SSSD Binder Password if exists in cluster_data or None."""
    sssd_binder_password = None
    if sssd_binder_password_data := cluster_data.get("sssdBinderPassword"):
        sssd_binder_password = sssd_binder_password_data
    return sssd_binder_password
