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


import typer

from vantage_cli.clouds.cudo_compute.utils import get_datacenter_id_from_credentials

from .templates import INIT_SCRIPT


async def init_project_and_head_node(
    ctx,
    project_name: str,
    vm_specs: list,
):
    """Create a project with the required resources."""
    # Create project - you'll need to get billing_account_id from settings or pass it
    billing_accounts = await ctx.obj.cudo_sdk.list_billing_accounts()
    if not billing_accounts:
        raise typer.Exit("No billing accounts available")
    billing_account_id = billing_accounts[0]["id"]
    
    project_data = {
        "id": project_name,
        "billingAccountId": billing_account_id,
    }
    project = await ctx.obj.cudo_sdk.create_project(project_data=project_data)
    project_id = project["id"]
    
    # Get datacenter_id from credentials, or use first available
    from vantage_cli.clouds.cudo_compute.sdk import CudoComputeSDK
    data_center_id = get_datacenter_id_from_credentials()
    
    if not data_center_id:
        # Fall back to first available data center
        data_centers = await ctx.obj.cudo_sdk.list_vm_data_centers()
        if not data_centers:
            raise typer.Exit("No data centers available")
        data_center_id = data_centers[0]["id"]
        print(f"ℹ️  No datacenter_id in credentials, using: {data_center_id}")
    else:
        print(f"✓ Using datacenter from credentials: {data_center_id}")
    
    # Create network
    network_id = "vantage-network"
    network = await ctx.obj.cudo_sdk.create_network(
        project_id=project_id,
        network_id=network_id,
        data_center_id=data_center_id,
        ip_range="10.0.0.0/16",
    )
    
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
    
    # Get image ID for Ubuntu 24.04 LTS
    images = await ctx.obj.cudo_sdk.list_public_vm_images()
    ubuntu_image = next((img for img in images if "Ubuntu 24.04" in img.get("name", "")), None)
    if not ubuntu_image:
        raise typer.Exit("Ubuntu 24.04 LTS image not found")
    image_id = ubuntu_image["id"]
    
    # Get SSH keys
    ssh_keys = await ctx.obj.cudo_sdk.list_ssh_keys()
    ssh_key_ids = [key["id"] for key in ssh_keys[:1]] if ssh_keys else []
    
    # Get available machine types for the data center
    all_machine_types = await ctx.obj.cudo_sdk.list_vm_machine_types(project_id=project_id)
    if not all_machine_types:
        raise typer.Exit("No machine types available")
    
    # Filter machine types for the selected data center
    dc_machine_types = [mt for mt in all_machine_types if mt.get("dataCenterId") == data_center_id]
    
    if not dc_machine_types:
        print(f"⚠️  No machine types found for data center {data_center_id}")
        print(f"Available data centers with machine types:")
        dc_set = set(mt.get("dataCenterId") for mt in all_machine_types)
        for dc in dc_set:
            print(f"  - {dc}")
        # Use first available data center
        data_center_id = list(dc_set)[0]
        dc_machine_types = [mt for mt in all_machine_types if mt.get("dataCenterId") == data_center_id]
        print(f"Using data center: {data_center_id}")
        print(f"Available machine types in {data_center_id}:")
        for mt in dc_machine_types[:5]:  # Show first 5
            print(f"  - {mt.get('machineType')} (CPU: {mt.get('cpuModel')}, GPU: {mt.get('gpuModel')})")
    
    # Create VM with the specified specs
    vm_spec = vm_specs[0] if vm_specs else {}
    machine_type = vm_spec.get("machine_type")
    
    # Validate the machine type exists in the data center
    if machine_type:
        machine_type_valid = any(mt.get("machineType") == machine_type for mt in dc_machine_types)
        if not machine_type_valid:
            print(f"⚠️  Requested machine type '{machine_type}' not available in {data_center_id}")
            machine_type = None  # Will be auto-selected below
    
    if not machine_type:
        # Pick the first machine type that supports the requested resources
        requested_vcpus = vm_spec.get("vcpus", 2)
        requested_memory = vm_spec.get("memory_gib", 4)
        requested_gpus = vm_spec.get("gpus", 0)
        
        # Find a suitable machine type
        for mt in dc_machine_types:
            min_vcpu = mt.get("minVcpu", 0)
            min_memory = mt.get("minMemoryGib", 0)
            max_vcpu = mt.get("maxVcpuFree", 999)
            max_memory = mt.get("maxMemoryGibFree", 999)
            max_gpu = mt.get("maxGpuFree", 0)
            
            # Skip GPU machine types if we don't need GPUs
            if requested_gpus == 0 and max_gpu > 0:
                continue
            
            # Check if this machine type can support our requirements
            if (min_vcpu <= requested_vcpus <= max_vcpu and 
                min_memory <= requested_memory <= max_memory):
                machine_type = mt["machineType"]
                print(f"✓ Selected machine type: {machine_type} (supports {requested_vcpus} vCPUs, {requested_memory} GiB RAM)")
                break
        
        if not machine_type:
            # Just use the first available one
            machine_type = dc_machine_types[0]["machineType"]
            print(f"⚠️  Using first available machine type: {machine_type}")
    
    vm_id = vm_spec.get("name", "vantage-testvm")
    
    print(f"\n🔧 VM Configuration:")
    print(f"  Data Center: {data_center_id}")
    print(f"  Machine Type: {machine_type}")
    print(f"  Image: {image_id}")
    print(f"  vCPUs: {vm_spec.get('vcpus', 2)}")
    print(f"  Memory: {vm_spec.get('memory_gib', 4)} GiB")
    print(f"  Network: {network['id']}")
    print(f"  Security Group: {security_group['id']}")
    
    vm = await ctx.obj.cudo_sdk.create_vm(
        project_id=project_id,
        vm_id=vm_id,
        data_center_id=data_center_id,
        machine_type=machine_type,
        boot_disk_image_id=image_id,
        vcpus=vm_spec.get("vcpus", 2),
        memory_gib=vm_spec.get("memory_gib", 4),
        gpus=vm_spec.get("gpus", 0),
        boot_disk_size_gib=vm_spec.get("boot_disk_size_gib", 20),
        ssh_key_source="SSH_KEY_SOURCE_USER",
        start_script=INIT_SCRIPT,
        nics=[{
            "assignPublicIp": False,
            "networkId": network["id"],
            "securityGroupIds": [security_group["id"]],
        }],
    )
    
    return vm.get("id")



async def delete_project_and_all_resources(ctx, project_id: str) -> None:
    """Delete a project and all its resources."""
    try:
        await ctx.obj.cudo_sdk.delete_project(project_id=project_id)
    except Exception as e:
        ctx.obj.console.print(f"[bold red]Error:[/bold red] Failed to delete project: {e}")
        raise typer.Exit(code=1)