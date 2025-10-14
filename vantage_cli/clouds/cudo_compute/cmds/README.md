# Cudo Compute Commands Implementation

This directory contains command implementations for all Cudo Compute resources.

## Implementation Status

### Completed (with examples)
- ✅ **project/** - All CRUD operations (list, get, create, update, delete)

### Patterns Implemented

Each resource follows the same pattern:

1. **list.py** - List all resources of this type
2. **get.py** - Get details of a specific resource
3. **create.py** - Create a new resource
4. **update.py** - Update an existing resource
5. **delete.py** - Delete a resource

### SDK Methods Available

All SDK methods are implemented in `../sdk.py`:

**Projects:**
- `list_projects(page_token, page_size)`
- `get_project(project_id)`
- `create_project(project_data)`
- `update_project(project_id, billing_account_id)`
- `delete_project(project_id)`

**Clusters:**
- `list_clusters(project_id, page_number, page_size)`
- `get_cluster(project_id, cluster_id)`
- `create_cluster(project_id, cluster_id, data_center_id, machine_type_id, machine_count, **kwargs)`
- `update_cluster(project_id, cluster_id, **kwargs)`
- `delete_cluster(project_id, cluster_id)`

**Machines (Bare Metal):**
- `list_machines(project_id, page_number, page_size)`
- `get_machine(project_id, machine_id)`
- `create_machine(project_id, machine_id, data_center_id, machine_type_id, os, **kwargs)`
- `update_machine(project_id, machine_id, **kwargs)`
- `delete_machine(project_id, machine_id)`

**Virtual Machines:**
- `list_vms(project_id, network_id)`
- `get_vm(project_id, vm_id)`
- `create_vm(project_id, vm_id, data_center_id, machine_type, boot_disk_image_id, vcpus, memory_gib, gpus, **kwargs)`
- `update_vm(project_id, vm_id, **kwargs)`
- `terminate_vm(project_id, vm_id)` (delete)
- `start_vm(project_id, vm_id)`
- `stop_vm(project_id, vm_id)`
- `reboot_vm(project_id, vm_id)`
- `resize_vm(project_id, vm_id, vcpus, memory_gib)`
- `connect_vm(project_id, vm_id, connection_id)`
- `monitor_vm(project_id, vm_id)`

**Networks:**
- `list_networks(project_id, page_number, page_size)`
- `get_network(project_id, network_id)`
- `create_network(project_id, network_id, data_center_id, ip_range)`
- `update_network(project_id, network_id, **kwargs)`
- `delete_network(project_id, network_id)`

**Security Groups:**
- `list_security_groups(project_id, data_center_id, page_number, page_size)`
- `get_security_group(project_id, security_group_id)`
- `create_security_group(project_id, security_group_data)`
- `update_security_group(project_id, security_group_id, **kwargs)`
- `delete_security_group(project_id, security_group_id)`

**Images:**
- `list_public_vm_images()`
- `list_private_vm_images(project_id, page_number, page_size)`
- `get_private_vm_image(project_id, image_id)`
- `create_private_vm_image(project_id, vm_id, image_id, description)`
- `delete_private_vm_image(project_id, image_id)`

**Data Centers:**
- `list_vm_data_centers()`
- `get_data_center(data_center_id)`

## Command Template

```python
# Copyright (C) 2025 Vantage Compute Corporation
# <license header>
"""<Operation> Cudo Compute <resource> command."""

import logging
import typer

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings
from vantage_cli.sdk.cloud_credential.crud import cloud_credential_sdk

from ...sdk import CudoComputeSDK

logger = logging.getLogger(__name__)
CLOUD = "cudo-compute"


@attach_settings
@attach_persona
async def <operation>_<resource>(
    ctx: typer.Context,
    # Add parameters here
) -> None:
    """<Description>."""

    cudo_credential = cloud_credential_sdk.get_default(cloud_name=CLOUD)
    if cudo_credential is None:
        logger.debug(f"[bold red]Error:[/bold red] No default credential found for '{CLOUD}'")
        logger.debug(f"Run: vantage cloud credential create --cloud {CLOUD}")
        raise typer.Exit(code=1)

    cudo_sdk = CudoComputeSDK(api_key=cudo_credential.credentials_data["api_key"])

    try:
        result = await cudo_sdk.<operation>_<resource>(...)
        # Handle result
    except Exception as e:
        logger.debug(f"[bold red]Error:[/bold red] Failed to <operation> <resource>: {e}")
        raise typer.Exit(code=1)

    ctx.obj.formatter.render_list(
        data=result,
        resource_name="<Resource Name>",
    )
```

## Integration

Commands are automatically discovered and registered by the parent `app.py` if they export a typer app.

## Testing

Test each command with:

```bash
uv run vantage cloud cudo-compute <resource> <operation> --help
```
