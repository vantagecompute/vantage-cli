# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Cluster management commands for Vantage CLI."""

from vantage_cli import AsyncTyper

from .create import create_cluster
from .delete import delete_cluster
from .get import get_cluster
from .list import list_clusters

# Create the cluster command group
cluster_app = AsyncTyper(
    name="clusters",
    help="Manage Vantage compute clusters for high-performance computing workloads.",
    context_settings={
        "allow_extra_args": True,
        "allow_interspersed_args": True,
        "ignore_unknown_options": True,
    },
)

# Register subcommands directly
cluster_app.command("create")(create_cluster)
cluster_app.command("delete")(delete_cluster)
cluster_app.command("get")(get_cluster)
cluster_app.command("list")(list_clusters)
