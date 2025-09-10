# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Cluster management commands for Vantage CLI."""

from vantage_cli import AsyncTyper

from .create import create_cluster
from .delete import delete_cluster
from .federation import federation_app
from .get import get_cluster
from .list import list_clusters

# Create the cluster command group
cluster_app = AsyncTyper(
    name="cluster",
    help="Manage Vantage compute clusters for high-performance computing workloads.",
    invoke_without_command=True,
    no_args_is_help=True,
)

# Register subcommands directly
cluster_app.command("create")(create_cluster)
cluster_app.command("delete")(delete_cluster)
cluster_app.command("get")(get_cluster)
cluster_app.command("list")(list_clusters)

# Add federation as a nested command group
cluster_app.add_typer(federation_app, name="federation")
