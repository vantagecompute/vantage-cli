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
"""Cudo Compute cloud provider commands."""

from vantage_cli import AsyncTyper

# Import command functions
from .cmds.project.list import list_projects
from .cmds.project.get import get_project
from .cmds.project.create import create_project
from .cmds.project.update import update_project
from .cmds.project.delete import delete_project

from .cmds.cluster.list import list_clusters
from .cmds.cluster.get import get_cluster
from .cmds.cluster.create import create_cluster
from .cmds.cluster.update import update_cluster
from .cmds.cluster.delete import delete_cluster

from .cmds.vm.list import list_vms
from .cmds.vm.get import get_vm
from .cmds.vm.create import create_vm
from .cmds.vm.update import update_vm
from .cmds.vm.delete import delete_vm

from .cmds.metal.list import list_metal
from .cmds.metal.get import get_metal
from .cmds.metal.create import create_metal
from .cmds.metal.update import update_metal
from .cmds.metal.delete import delete_metal

from .cmds.network.list import list_networks
from .cmds.network.get import get_network
from .cmds.network.create import create_network
from .cmds.network.update import update_network
from .cmds.network.delete import delete_network

from .cmds.security_group.list import list_security_groups
from .cmds.security_group.get import get_security_group
from .cmds.security_group.create import create_security_group
from .cmds.security_group.update import update_security_group
from .cmds.security_group.delete import delete_security_group

from .cmds.data_center.list import list_data_centers
from .cmds.data_center.get import get_data_center

from .cmds.image.list import list_images
from .cmds.image.get import get_image

# Create main app
app = AsyncTyper(
    name="cudo-compute",
    help="Cudo Compute cloud provider commands",
    no_args_is_help=True,
)

# Create sub-apps for each resource type
projects_app = AsyncTyper(name="projects", help="Manage Cudo Compute projects", no_args_is_help=True)
clusters_app = AsyncTyper(name="clusters", help="Manage Cudo Compute clusters", no_args_is_help=True)
vms_app = AsyncTyper(name="vms", help="Manage Cudo Compute virtual machines", no_args_is_help=True)
metal_app = AsyncTyper(name="metal", help="Manage Cudo Compute bare-metal machines", no_args_is_help=True)
networks_app = AsyncTyper(name="networks", help="Manage Cudo Compute networks", no_args_is_help=True)
security_groups_app = AsyncTyper(name="security-groups", help="Manage Cudo Compute security groups", no_args_is_help=True)
data_centers_app = AsyncTyper(name="data-centers", help="Query Cudo Compute data centers", no_args_is_help=True)
images_app = AsyncTyper(name="images", help="Query Cudo Compute VM images", no_args_is_help=True)

# Register project commands
projects_app.command("list")(list_projects)
projects_app.command("get")(get_project)
projects_app.command("create")(create_project)
projects_app.command("update")(update_project)
projects_app.command("delete")(delete_project)

# Register cluster commands
clusters_app.command("list")(list_clusters)
clusters_app.command("get")(get_cluster)
clusters_app.command("create")(create_cluster)
clusters_app.command("update")(update_cluster)
clusters_app.command("delete")(delete_cluster)

# Register VM commands
vms_app.command("list")(list_vms)
vms_app.command("get")(get_vm)
vms_app.command("create")(create_vm)
vms_app.command("update")(update_vm)
vms_app.command("delete")(delete_vm)

# Register metal commands
metal_app.command("list")(list_metal)
metal_app.command("get")(get_metal)
metal_app.command("create")(create_metal)
metal_app.command("update")(update_metal)
metal_app.command("delete")(delete_metal)

# Register network commands
networks_app.command("list")(list_networks)
networks_app.command("get")(get_network)
networks_app.command("create")(create_network)
networks_app.command("update")(update_network)
networks_app.command("delete")(delete_network)

# Register security group commands
security_groups_app.command("list")(list_security_groups)
security_groups_app.command("get")(get_security_group)
security_groups_app.command("create")(create_security_group)
security_groups_app.command("update")(update_security_group)
security_groups_app.command("delete")(delete_security_group)

# Register data center commands
data_centers_app.command("list")(list_data_centers)
data_centers_app.command("get")(get_data_center)

# Register image commands
images_app.command("list")(list_images)
images_app.command("get")(get_image)

# Add sub-apps to main app
app.add_typer(projects_app)
app.add_typer(clusters_app)
app.add_typer(vms_app)
app.add_typer(metal_app)
app.add_typer(networks_app)
app.add_typer(security_groups_app)
app.add_typer(data_centers_app)
app.add_typer(images_app)

# Add shortcut aliases for list commands (so users can type `vantage cloud cudo-compute vms` instead of `vantage cloud cudo-compute vms list`)
app.command("projects", help="List Cudo Compute projects (alias for 'projects list')")(list_projects)
app.command("clusters", help="List Cudo Compute clusters (alias for 'clusters list')")(list_clusters)
app.command("vms", help="List Cudo Compute VMs (alias for 'vms list')")(list_vms)
app.command("metal", help="List Cudo Compute bare-metal machines (alias for 'metal list')")(list_metal)
app.command("networks", help="List Cudo Compute networks (alias for 'networks list')")(list_networks)
app.command("security-groups", help="List Cudo Compute security groups (alias for 'security-groups list')")(list_security_groups)
app.command("data-centers", help="List Cudo Compute data centers (alias for 'data-centers list')")(list_data_centers)
app.command("images", help="List Cudo Compute VM images (alias for 'images list')")(list_images)
