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
