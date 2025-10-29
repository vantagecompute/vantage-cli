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

from .cmds.billing_account.get import get_billing_account
from .cmds.billing_account.list import list_billing_accounts
from .cmds.cluster.create import create_cluster
from .cmds.cluster.delete import delete_cluster
from .cmds.cluster.get import get_cluster
from .cmds.cluster.list import list_clusters
from .cmds.cluster.update import update_cluster
from .cmds.data_center.get import get_data_center
from .cmds.data_center.list import list_data_centers
from .cmds.disk.create import create_disk
from .cmds.disk.delete import delete_disk
from .cmds.disk.get import get_disk
from .cmds.disk.list import list_disks
from .cmds.disk.update import update_disk
from .cmds.image.get import get_image
from .cmds.image.list import list_images
from .cmds.machine.create import create_machine
from .cmds.machine.delete import delete_machine
from .cmds.machine.get import get_machine
from .cmds.machine.list import list_machines
from .cmds.machine.update import update_machine
from .cmds.machine_type.get import get_machine_type
from .cmds.machine_type.list import list_machine_types
from .cmds.network.create import create_network
from .cmds.network.delete import delete_network
from .cmds.network.get import get_network
from .cmds.network.list import list_networks
from .cmds.network.update import update_network
from .cmds.project.create import create_project
from .cmds.project.delete import delete_project
from .cmds.project.get import get_project

# Import command functions
from .cmds.project.list import list_projects
from .cmds.project.update import update_project
from .cmds.security_group.create import create_security_group
from .cmds.security_group.delete import delete_security_group
from .cmds.security_group.get import get_security_group
from .cmds.security_group.list import list_security_groups
from .cmds.security_group.update import update_security_group
from .cmds.security_group_rule.create import create_security_group_rule
from .cmds.security_group_rule.delete import delete_security_group_rule
from .cmds.security_group_rule.get import get_security_group_rule
from .cmds.security_group_rule.list import list_security_group_rules
from .cmds.security_group_rule.update import update_security_group_rule
from .cmds.sshkey.create import create_ssh_key
from .cmds.sshkey.delete import delete_ssh_key
from .cmds.sshkey.get import get_ssh_key
from .cmds.sshkey.list import list_ssh_keys
from .cmds.vm.create import create_vm
from .cmds.vm.delete import delete_vm
from .cmds.vm.get import get_vm
from .cmds.vm.list import list_vms
from .cmds.vm.update import update_vm
from .cmds.vm_data_center.get import get_vm_data_center
from .cmds.vm_data_center.list import list_vm_data_centers
from .cmds.vm_machine_type.get import get_vm_machine_type
from .cmds.vm_machine_type.list import list_vm_machine_types
from .cmds.volume.create import create_volume
from .cmds.volume.delete import delete_volume
from .cmds.volume.get import get_volume
from .cmds.volume.list import list_volumes
from .cmds.volume.update import update_volume

# Create main app
app = AsyncTyper(
    name="cudo-compute",
    help="Cudo Compute cloud provider commands",
    no_args_is_help=True,
)

# Create sub-apps for each resource type (singular names)
project_app = AsyncTyper(name="project", help="Manage Cudo Compute projects", no_args_is_help=True)
cluster_app = AsyncTyper(name="cluster", help="Manage Cudo Compute clusters", no_args_is_help=True)
vm_app = AsyncTyper(name="vm", help="Manage Cudo Compute virtual machines", no_args_is_help=True)
machine_app = AsyncTyper(
    name="machine", help="Manage Cudo Compute bare-metal machines", no_args_is_help=True
)
network_app = AsyncTyper(name="network", help="Manage Cudo Compute networks", no_args_is_help=True)
security_group_app = AsyncTyper(
    name="security-group", help="Manage Cudo Compute security groups", no_args_is_help=True
)
security_group_rule_app = AsyncTyper(
    name="sg-rule", help="Manage Cudo Compute security group rules", no_args_is_help=True
)
vm_data_center_app = AsyncTyper(
    name="vm-data-center", help="Query VM data centers", no_args_is_help=True
)
machine_type_app = AsyncTyper(
    name="machine-type", help="Query bare-metal machine types", no_args_is_help=True
)
vm_machine_type_app = AsyncTyper(
    name="vm-machine-type", help="Query VM machine types", no_args_is_help=True
)
data_center_app = AsyncTyper(
    name="data-center", help="Query Cudo Compute data centers", no_args_is_help=True
)
image_app = AsyncTyper(name="image", help="Query Cudo Compute VM images", no_args_is_help=True)
disk_app = AsyncTyper(name="disk", help="Manage Cudo Compute storage disks", no_args_is_help=True)
volume_app = AsyncTyper(
    name="volume", help="Manage Cudo Compute NFS volumes", no_args_is_help=True
)
sshkey_app = AsyncTyper(name="sshkey", help="Manage Cudo Compute SSH keys", no_args_is_help=True)
billing_account_app = AsyncTyper(
    name="billing-account", help="Manage Cudo Compute billing accounts", no_args_is_help=True
)

# Register project commands
project_app.command("list")(list_projects)
project_app.command("get")(get_project)
project_app.command("create")(create_project)
project_app.command("update")(update_project)
project_app.command("delete")(delete_project)

# Register cluster commands
cluster_app.command("list")(list_clusters)
cluster_app.command("get")(get_cluster)
cluster_app.command("create")(create_cluster)
cluster_app.command("update")(update_cluster)
cluster_app.command("delete")(delete_cluster)

# Register VM commands
vm_app.command("list")(list_vms)
vm_app.command("get")(get_vm)
vm_app.command("create")(create_vm)
vm_app.command("update")(update_vm)
vm_app.command("delete")(delete_vm)

# Register machine commands
machine_app.command("list")(list_machines)
machine_app.command("get")(get_machine)
machine_app.command("create")(create_machine)
machine_app.command("update")(update_machine)
machine_app.command("delete")(delete_machine)

# Register network commands
network_app.command("list")(list_networks)
network_app.command("get")(get_network)
network_app.command("create")(create_network)
network_app.command("update")(update_network)
network_app.command("delete")(delete_network)

# Register security group commands
security_group_app.command("list")(list_security_groups)
security_group_app.command("get")(get_security_group)
security_group_app.command("create")(create_security_group)
security_group_app.command("update")(update_security_group)
security_group_app.command("delete")(delete_security_group)

# Register security group rule commands
security_group_rule_app.command("list")(list_security_group_rules)
security_group_rule_app.command("get")(get_security_group_rule)
security_group_rule_app.command("create")(create_security_group_rule)
security_group_rule_app.command("update")(update_security_group_rule)
security_group_rule_app.command("delete")(delete_security_group_rule)

# Register VM data center commands
vm_data_center_app.command("list")(list_vm_data_centers)
vm_data_center_app.command("get")(get_vm_data_center)

# Register machine type commands
machine_type_app.command("list")(list_machine_types)
machine_type_app.command("get")(get_machine_type)

# Register VM machine type commands (alias)
vm_machine_type_app.command("list")(list_vm_machine_types)
vm_machine_type_app.command("get")(get_vm_machine_type)

# Register data center commands
data_center_app.command("list")(list_data_centers)
data_center_app.command("get")(get_data_center)

# Register image commands
image_app.command("list")(list_images)
image_app.command("get")(get_image)

# Register disk commands
disk_app.command("list")(list_disks)
disk_app.command("get")(get_disk)
disk_app.command("create")(create_disk)
disk_app.command("update")(update_disk)
disk_app.command("delete")(delete_disk)

# Register volume commands
volume_app.command("list")(list_volumes)
volume_app.command("get")(get_volume)
volume_app.command("create")(create_volume)
volume_app.command("update")(update_volume)
volume_app.command("delete")(delete_volume)

# Register sshkey commands
sshkey_app.command("list")(list_ssh_keys)
sshkey_app.command("get")(get_ssh_key)
sshkey_app.command("create")(create_ssh_key)
sshkey_app.command("delete")(delete_ssh_key)

# Register billing account commands
billing_account_app.command("list")(list_billing_accounts)
billing_account_app.command("get")(get_billing_account)

# Add sub-apps to main app (singular)
app.add_typer(project_app)
app.add_typer(cluster_app)
app.add_typer(vm_app)
app.add_typer(machine_app)
app.add_typer(network_app)
app.add_typer(security_group_app)
app.add_typer(security_group_rule_app)
app.add_typer(vm_data_center_app)
app.add_typer(machine_type_app)
app.add_typer(vm_machine_type_app)
app.add_typer(data_center_app)
app.add_typer(image_app)
app.add_typer(disk_app)
app.add_typer(volume_app)
app.add_typer(sshkey_app)
app.add_typer(billing_account_app)

# Add plural aliases for list commands (so users can type `vantage cloud cudo-compute projects` instead of `vantage cloud cudo-compute project list`)
app.command("projects", help="List Cudo Compute projects (alias for 'project list')", hidden=True)(
    list_projects
)
app.command("clusters", help="List Cudo Compute clusters (alias for 'cluster list')", hidden=True)(
    list_clusters
)
app.command("vms", help="List Cudo Compute VMs (alias for 'vm list')", hidden=True)(list_vms)
app.command(
    "machines",
    help="List Cudo Compute bare-metal machines (alias for 'machine list')",
    hidden=True,
)(list_machines)
app.command("networks", help="List Cudo Compute networks (alias for 'network list')", hidden=True)(
    list_networks
)
app.command(
    "security-groups",
    help="List Cudo Compute security groups (alias for 'security-group list')",
    hidden=True,
)(list_security_groups)
app.command(
    "vm-data-centers", help="List VM data centers (alias for 'vm-data-center list')", hidden=True
)(list_vm_data_centers)
app.command(
    "machine-types",
    help="List bare-metal machine types (alias for 'machine-type list')",
    hidden=True,
)(list_machine_types)
app.command(
    "vm-machine-types",
    help="List VM machine types (alias for 'vm-machine-type list')",
    hidden=True,
)(list_vm_machine_types)
app.command(
    "data-centers",
    help="List Cudo Compute data centers (alias for 'data-center list')",
    hidden=True,
)(list_data_centers)
app.command("images", help="List Cudo Compute VM images (alias for 'image list')", hidden=True)(
    list_images
)
app.command("disks", help="List Cudo Compute storage disks (alias for 'disk list')", hidden=True)(
    list_disks
)
app.command(
    "volumes", help="List Cudo Compute NFS volumes (alias for 'volume list')", hidden=True
)(list_volumes)
app.command("sshkeys", help="List Cudo Compute SSH keys (alias for 'sshkey list')", hidden=True)(
    list_ssh_keys
)
app.command(
    "billing-accounts",
    help="List Cudo Compute billing accounts (alias for 'billing-account list')",
    hidden=True,
)(list_billing_accounts)
