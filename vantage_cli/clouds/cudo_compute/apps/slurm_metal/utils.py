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
"""Utility functions for Cudo Compute SLURM K8S deployments."""

import asyncio
from pathlib import Path

import typer


def get_local_ssh_public_keys() -> list[str]:
    """Read SSH public keys from the local ~/.ssh directory.

    Returns:
        List of SSH public key strings
    """
    ssh_keys = []
    ssh_dir = Path.home() / ".ssh"

    # Common public key file names
    key_files = ["id_rsa.pub", "id_ed25519.pub", "id_ecdsa.pub", "id_dsa.pub"]

    for key_file in key_files:
        key_path = ssh_dir / key_file
        if key_path.exists():
            try:
                with open(key_path, "r") as f:
                    key_content = f.read().strip()
                    if key_content:
                        ssh_keys.append(key_content)
            except Exception:
                # Skip files that can't be read
                pass

    return ssh_keys


async def init_project_and_head_node(
    ctx: typer.Context,
    project_name: str,
    init_script: str,
    data_center_id: str,
) -> str:
    """Create a project with the required resources."""
    # Create project - you'll need to get billing_account_id from settings or pass it
    billing_accounts = await ctx.obj.cudo_sdk.list_billing_accounts()
    if not billing_accounts:
        raise typer.Exit(code=1)
    billing_account_id = billing_accounts[0].id

    project_data = {
        "id": project_name,
        "billingAccountId": billing_account_id,
    }
    project = await ctx.obj.cudo_sdk.create_project(project_data=project_data)
    project_id = project.id

    # Create network
    network_id = "vantage-slurm-on-metal-nat-network"
    network = await ctx.obj.cudo_sdk.create_network(
        project_id=project_id,
        network_id=network_id,
        data_center_id=data_center_id,
        ip_range="10.0.0.0/16",
    )

    # Wait for network to be active before proceeding
    ctx.obj.console.print("⏳ Waiting for network to be active...")
    max_wait = 120  # 2 minutes
    wait_interval = 5  # seconds
    elapsed = 0

    while elapsed < max_wait:
        network = await ctx.obj.cudo_sdk.get_network(
            project_id=project_id,
            network_id=network_id,
        )
        if network.state == "ACTIVE":
            ctx.obj.console.print("✅ Network is active")
            break
        await asyncio.sleep(wait_interval)
        elapsed += wait_interval
    else:
        raise Exception(f"Network did not become active after {max_wait} seconds")

    # Create security group with allow-all ingress and egress rules
    security_group_id = "vantage-sg-allow-all"
    allow_all_rules = [
        {
            "protocol": "PROTOCOL_ALL",
            "ruleType": "RULE_TYPE_INBOUND",
            "ipRangeCidr": "0.0.0.0/0",
        },
        {
            "protocol": "PROTOCOL_ALL",
            "ruleType": "RULE_TYPE_OUTBOUND",
            "ipRangeCidr": "0.0.0.0/0",
        },
    ]

    security_group = await ctx.obj.cudo_sdk.create_security_group(
        project_id=project_id,
        security_group_id=security_group_id,
        data_center_id=data_center_id,
        description="Allow all ingress and egress traffic",
        rules=allow_all_rules,
    )

    image_id = "ubuntu-2404"

    # Get local SSH public keys
    # local_ssh_keys = get_local_ssh_public_keys()
    # if local_ssh_keys:
    #    ctx.obj.console.print(f"📝 Found {len(local_ssh_keys)} local SSH key(s) to add to VM")
    # else:
    #    ctx.obj.console.print(f"⚠️  [yellow]Warning:[/yellow] No local SSH keys found in ~/.ssh/")

    # Get available machine types for the data center
    dc_machine_types = await ctx.obj.cudo_sdk.list_vm_machine_types(
        project_id=project_id, data_center_id=data_center_id
    )

    # Create VM with the specified specs

    requested_vcpus = 8
    requested_memory = 32
    requested_gpus = 0

    machine_type = dc_machine_types[0].machine_type
    # Find a suitable machine type
    for mt in dc_machine_types:
        min_vcpu = mt.min_vcpu or 0
        min_memory = mt.min_memory_gib or 0
        max_vcpu = mt.max_vcpu_free or 999
        max_memory = mt.max_memory_gib_free or 999
        max_gpu = mt.max_gpu_free or 0

        # Skip GPU machine types if we don't need GPUs
        if requested_gpus == 0 and max_gpu > 0:
            continue

        # Check if this machine type can support our requirements
        if (
            min_vcpu <= requested_vcpus <= max_vcpu
            and min_memory <= requested_memory <= max_memory
        ):
            machine_type = mt.machine_type
            break

    vm = await ctx.obj.cudo_sdk.create_vm(
        project_id=project_id,
        vm_id=project_name + "-head-node",
        data_center_id=data_center_id,
        machine_type=machine_type,
        boot_disk_image_id=image_id,
        vcpus=4,
        memory_gib=16,
        gpus=0,
        boot_disk_size_gib=20,
        ssh_key_source="SSH_KEY_SOURCE_USER",
        start_script=init_script,  # Use minimal bootstrap instead of full script
        # custom_ssh_keys=local_ssh_keys,  # Disabled: causes 403 when combined with large start_script
        nics=[
            {
                "assignPublicIp": True,
                "networkId": network.id,
                "securityGroupIds": [security_group.id],
            }
        ],
    )

    return vm.id


async def delete_project_and_all_resources(ctx, project_id: str) -> None:
    """Delete a project and all its resources."""
    try:
        await ctx.obj.cudo_sdk.delete_project(project_id=project_id)
    except Exception as e:
        ctx.obj.console.print(f"[bold red]Error:[/bold red] Failed to delete project: {e}")
        raise typer.Exit(code=1)
