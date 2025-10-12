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
"""Cudo Compute SDK for managing VMs and resources via their REST API.

Based on the Cudo Compute OpenAPI specification:
https://raw.githubusercontent.com/cudoventures/cudo-compute-docs/refs/heads/main/api-reference/openapi.json
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class CudoComputeSDK:
    """SDK for interacting with the Cudo Compute REST API.
    
    This SDK provides methods to manage virtual machines, data centers,
    machine types, images, networks, and other cloud resources on Cudo Compute.
    
    Authentication is done via bearer token (API key).
    
    API Base URL: https://rest.compute.cudo.org
    """
    
    BASE_URL = "https://rest.compute.cudo.org"
    
    def __init__(self, api_key: str):
        """Initialize the Cudo Compute SDK.
        
        Args:
            api_key: Cudo Compute API key for authentication
        """
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        logger.debug("Initialized CudoComputeSDK")
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    # ========================================================================
    # Virtual Machines
    # ========================================================================
    
    async def list_vms(
        self,
        project_id: str,
        network_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List all virtual machines in a project.
        
        Args:
            project_id: Project ID to list VMs from
            network_id: Optional network ID to filter VMs
            
        Returns:
            List of VM dictionaries
        """
        params = {}
        if network_id:
            params["networkId"] = network_id
        
        response = await self.client.get(
            f"/v1/projects/{project_id}/vms",
            params=params,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("VMs", [])
    
    async def get_vm(
        self,
        project_id: str,
        vm_id: str,
    ) -> Dict[str, Any]:
        """Get details of a specific virtual machine.
        
        Args:
            project_id: Project ID
            vm_id: Virtual machine ID
            
        Returns:
            VM details including pricing information
        """
        response = await self.client.get(
            f"/v1/projects/{project_id}/vms/{vm_id}"
        )
        response.raise_for_status()
        return response.json()
    
    async def create_vm(
        self,
        project_id: str,
        vm_id: str,
        data_center_id: str,
        machine_type: str,
        boot_disk_image_id: str,
        vcpus: int,
        memory_gib: int,
        gpus: int = 0,
        boot_disk_size_gib: Optional[int] = None,
        password: Optional[str] = None,
        ssh_key_source: Optional[str] = None,
        custom_ssh_keys: Optional[List[str]] = None,
        start_script: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        security_group_ids: Optional[List[str]] = None,
        storage_disk_ids: Optional[List[str]] = None,
        commitment_term: Optional[str] = None,
        expire_time: Optional[str] = None,
        ttl: Optional[str] = None,
        nics: Optional[List[Dict[str, Any]]] = None,
        validate_only: bool = False,
    ) -> Dict[str, Any]:
        """Create and start a new virtual machine.
        
        Args:
            project_id: Project ID to create VM in
            vm_id: Unique identifier for the VM
            data_center_id: Data center to create VM in
            machine_type: Machine type to use (e.g., 'standard', 'performance')
            boot_disk_image_id: Boot disk image ID (public or private image)
            vcpus: Number of vCPUs (must meet machine type requirements)
            memory_gib: Memory in GiB (must meet machine type requirements)
            gpus: Number of GPUs (default: 0)
            boot_disk_size_gib: Boot disk size in GiB (if not set, uses image default)
            password: Root/admin password (for Windows VMs or custom Linux setup)
            ssh_key_source: SSH key source - 'SSH_KEY_SOURCE_PROJECT', 'SSH_KEY_SOURCE_USER', or 'SSH_KEY_SOURCE_NONE'
            custom_ssh_keys: List of custom SSH public keys to add
            start_script: Startup script/cloud-init to run on first boot
            metadata: VM metadata key-value pairs
            security_group_ids: List of security group IDs (ignored if nics provided)
            storage_disk_ids: List of storage disk IDs to attach
            commitment_term: Commitment term ('COMMITMENT_TERM_NONE', 'COMMITMENT_TERM_1_MONTH', etc.)
            expire_time: Expiration time in ISO 8601 format
            ttl: Time to live duration string
            nics: List of network interface configurations with assignPublicIp, networkId, securityGroupIds
            validate_only: Only validate request without creating (default: False)
            
        Returns:
            Dict with created VM details and ID
            
        Example:
            >>> vm = await sdk.create_vm(
            ...     project_id="my-project",
            ...     vm_id="my-vm-001",
            ...     data_center_id="gb-bournemouth-1",
            ...     machine_type="standard",
            ...     boot_disk_image_id="ubuntu-2204-lts",
            ...     vcpus=2,
            ...     memory_gib=4,
            ...     gpus=0,
            ...     ssh_key_source="SSH_KEY_SOURCE_USER"
            ... )
        """
        body: Dict[str, Any] = {
            "dataCenterId": data_center_id,
            "machineType": machine_type,
            "vmId": vm_id,
            "bootDiskImageId": boot_disk_image_id,
            "vcpus": vcpus,
            "memoryGib": memory_gib,
            "gpus": gpus,
        }
        
        # Optional parameters
        if boot_disk_size_gib is not None:
            body["bootDiskSizeGib"] = boot_disk_size_gib
        if password:
            body["password"] = password
        if ssh_key_source:
            body["sshKeySource"] = ssh_key_source
        if custom_ssh_keys:
            body["customSshKeys"] = custom_ssh_keys
        if start_script:
            body["startScript"] = start_script
        if metadata:
            body["metadata"] = metadata
        if nics:
            body["nics"] = nics
        if security_group_ids and not nics:
            # security_group_ids is ignored if nics are provided
            body["securityGroupIds"] = security_group_ids
        if storage_disk_ids:
            body["storageDiskIds"] = storage_disk_ids
        if commitment_term:
            body["commitmentTerm"] = commitment_term
        if expire_time:
            body["expireTime"] = expire_time
        if ttl:
            body["ttl"] = ttl
        if validate_only:
            body["validateOnly"] = validate_only
        
        response = await self.client.post(
            f"/v1/projects/{project_id}/vm",
            json=body,
        )
        response.raise_for_status()
        return response.json()
    
    async def terminate_vm(
        self,
        project_id: str,
        vm_id: str,
    ) -> Dict[str, Any]:
        """Permanently delete a virtual machine.
        
        All data on the VM's boot disk will be lost.
        Attached storage disks will be detached but not deleted.
        
        Args:
            project_id: Project ID
            vm_id: Virtual machine ID to delete
            
        Returns:
            Empty response on success
        """
        response = await self.client.post(
            f"/v1/projects/{project_id}/vms/{vm_id}/terminate"
        )
        response.raise_for_status()
        return response.json()
    
    async def start_vm(
        self,
        project_id: str,
        vm_id: str,
    ) -> Dict[str, Any]:
        """Start a stopped virtual machine.
        
        Args:
            project_id: Project ID
            vm_id: Virtual machine ID
            
        Returns:
            Empty response on success
        """
        response = await self.client.post(
            f"/v1/projects/{project_id}/vms/{vm_id}/start"
        )
        response.raise_for_status()
        return response.json()
    
    async def stop_vm(
        self,
        project_id: str,
        vm_id: str,
    ) -> Dict[str, Any]:
        """Stop a running virtual machine.
        
        The VM can be started again later.
        
        Args:
            project_id: Project ID
            vm_id: Virtual machine ID
            
        Returns:
            Empty response on success
        """
        response = await self.client.post(
            f"/v1/projects/{project_id}/vms/{vm_id}/stop"
        )
        response.raise_for_status()
        return response.json()
    
    async def reboot_vm(
        self,
        project_id: str,
        vm_id: str,
    ) -> Dict[str, Any]:
        """Perform a soft reboot of a virtual machine.
        
        Args:
            project_id: Project ID
            vm_id: Virtual machine ID
            
        Returns:
            Empty response on success
        """
        response = await self.client.post(
            f"/v1/projects/{project_id}/vms/{vm_id}/reboot"
        )
        response.raise_for_status()
        return response.json()
    
    async def resize_vm(
        self,
        project_id: str,
        vm_id: str,
        vcpus: Optional[int] = None,
        memory_gib: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Resize a virtual machine.
        
        Size cannot be reduced while in a committed term.
        
        Args:
            project_id: Project ID
            vm_id: Virtual machine ID
            vcpus: New vCPU count
            memory_gib: New memory in GiB
            
        Returns:
            Updated VM details
        """
        params = {}
        if vcpus is not None:
            params["vcpus"] = vcpus
        if memory_gib is not None:
            params["memoryGib"] = memory_gib
        
        response = await self.client.post(
            f"/v1/projects/{project_id}/vms/{vm_id}/resize",
            params=params,
        )
        response.raise_for_status()
        return response.json()
    
    async def connect_vm(
        self,
        project_id: str,
        vm_id: str,
        connection_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get URL and token to connect to VM via web-based VNC console.
        
        Args:
            project_id: Project ID
            vm_id: Virtual machine ID
            connection_id: Optional connection ID
            
        Returns:
            Dict with connectUrl and token
        """
        params = {}
        if connection_id:
            params["connectionId"] = connection_id
        
        response = await self.client.get(
            f"/v1/projects/{project_id}/vms/{vm_id}/connect",
            params=params,
        )
        response.raise_for_status()
        return response.json()
    
    async def monitor_vm(
        self,
        project_id: str,
        vm_id: str,
    ) -> Dict[str, Any]:
        """Get live monitoring metrics for a virtual machine.
        
        Args:
            project_id: Project ID
            vm_id: Virtual machine ID
            
        Returns:
            Monitoring metrics data
        """
        response = await self.client.get(
            f"/v1/projects/{project_id}/vms/{vm_id}/monitor"
        )
        response.raise_for_status()
        return response.json()
    
    # ========================================================================
    # Data Centers
    # ========================================================================
    
    async def list_vm_data_centers(self) -> List[Dict[str, Any]]:
        """List all data centers available for virtual machines.
        
        Alias for list_data_centers() for backward compatibility.
        
        Returns:
            List of data center dictionaries
        """
        response = await self.client.get("/v1/vms/data-centers")
        response.raise_for_status()
        data = response.json()
        return data.get("dataCenters", [])
    
    
    async def list_vm_machine_types(
        self,
        project_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List all virtual machine types available.
        
        Args:
            project_id: Optional project ID for custom pricing
            
        Returns:
            List of machine type dictionaries
        """
        params = {}
        if project_id:
            params["projectId"] = project_id
        
        response = await self.client.get(
            "/v1/vms/machine-types",
            params=params,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("machineTypes", [])
    
    async def get_vm_machine_type(
        self,
        data_center_id: str,
        machine_type_id: str,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get details of a specific virtual machine type.
        
        Args:
            data_center_id: Data center ID
            machine_type_id: Machine type ID
            project_id: Optional project ID for custom pricing
            
        Returns:
            Machine type details with pricing
        """
        params = {}
        if project_id:
            params["projectId"] = project_id
        
        response = await self.client.get(
            f"/v1/vms/data-centers/{data_center_id}/machine_types/{machine_type_id}",
            params=params,
        )
        response.raise_for_status()
        return response.json()
    
    async def list_vm_gpu_models(self) -> List[Dict[str, Any]]:
        """List all GPU models available for virtual machines.
        
        Returns:
            List of GPU model dictionaries
        """
        response = await self.client.get("/v1/vms/gpu-models")
        response.raise_for_status()
        data = response.json()
        return data.get("gpuModels", [])
    
    # ========================================================================
    # Images
    # ========================================================================
    
    async def list_public_vm_images(self) -> List[Dict[str, Any]]:
        """List all public images available for virtual machines.
        
        Returns:
            List of image dictionaries
        """
        response = await self.client.get("/v1/vms/public-images")
        response.raise_for_status()
        data = response.json()
        return data.get("images", [])
    
    async def list_private_vm_images(
        self,
        project_id: str,
        page_number: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List private virtual machine images in a project.
        
        Args:
            project_id: Project ID
            page_number: Page number for pagination
            page_size: Results per page
            
        Returns:
            List of private image dictionaries
        """
        params = {}
        if page_number is not None:
            params["pageNumber"] = page_number
        if page_size is not None:
            params["pageSize"] = page_size
        
        response = await self.client.get(
            f"/v1/projects/{project_id}/images",
            params=params,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("images", [])
    
    async def create_private_vm_image(
        self,
        project_id: str,
        vm_id: str,
        image_id: str,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new private VM image from an existing VM's boot disk.
        
        Args:
            project_id: Project ID
            vm_id: Source VM ID
            image_id: New image ID
            description: Optional image description
            
        Returns:
            Created image details
        """
        params = {
            "vmId": vm_id,
            "id": image_id,
        }
        if description:
            params["description"] = description
        
        response = await self.client.post(
            f"/v1/projects/{project_id}/images",
            params=params,
        )
        response.raise_for_status()
        return response.json()
    
    async def delete_private_vm_image(
        self,
        project_id: str,
        image_id: str,
    ) -> Dict[str, Any]:
        """Delete a private virtual machine image.
        
        Args:
            project_id: Project ID
            image_id: Image ID to delete
            
        Returns:
            Empty response on success
        """
        response = await self.client.delete(
            f"/v1/projects/{project_id}/images/{image_id}"
        )
        response.raise_for_status()
        return response.json()
    
    # ========================================================================
    # Disks
    # ========================================================================
    
    async def list_disks(
        self,
        project_id: str,
        page_number: Optional[int] = None,
        page_size: Optional[int] = None,
        data_center_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List disks in a project.
        
        Args:
            project_id: Project ID
            page_number: Page number for pagination
            page_size: Results per page
            data_center_id: Optional data center filter
            
        Returns:
            List of disk dictionaries
        """
        params = {}
        if page_number is not None:
            params["pageNumber"] = page_number
        if page_size is not None:
            params["pageSize"] = page_size
        if data_center_id:
            params["dataCenterId"] = data_center_id
        
        response = await self.client.get(
            f"/v1/projects/{project_id}/disks",
            params=params,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("disks", [])
    
    async def create_disk(
        self,
        project_id: str,
        disk_id: str,
        data_center_id: str,
        size_gib: int,
        disk_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new virtual machine disk.
        
        Args:
            project_id: Project ID
            disk_id: Unique disk ID
            data_center_id: Data center ID
            size_gib: Disk size in GiB
            disk_type: Optional disk type
            
        Returns:
            Created disk details
        """
        body = {
            "id": disk_id,
            "dataCenterId": data_center_id,
            "sizeGib": size_gib,
        }
        if disk_type:
            body["diskType"] = disk_type
        
        response = await self.client.post(
            f"/v1/projects/{project_id}/disks",
            json=body,
        )
        response.raise_for_status()
        return response.json()
    
    async def delete_disk(
        self,
        project_id: str,
        disk_id: str,
    ) -> Dict[str, Any]:
        """Delete a virtual machine disk.
        
        The disk must be detached from any VMs first.
        
        Args:
            project_id: Project ID
            disk_id: Disk ID to delete
            
        Returns:
            Empty response on success
        """
        response = await self.client.delete(
            f"/v1/projects/{project_id}/disks/{disk_id}"
        )
        response.raise_for_status()
        return response.json()
    
    async def attach_disk(
        self,
        project_id: str,
        disk_id: str,
        vm_id: str,
    ) -> Dict[str, Any]:
        """Attach a disk to a virtual machine.
        
        Args:
            project_id: Project ID
            disk_id: Disk ID to attach
            vm_id: Target VM ID
            
        Returns:
            Empty response on success
        """
        response = await self.client.patch(
            f"/v1/projects/{project_id}/disk/{disk_id}/attach",
            params={"vmId": vm_id},
        )
        response.raise_for_status()
        return response.json()
    
    async def detach_disk(
        self,
        project_id: str,
        disk_id: str,
    ) -> Dict[str, Any]:
        """Detach a disk from a virtual machine.
        
        Args:
            project_id: Project ID
            disk_id: Disk ID to detach
            
        Returns:
            Empty response on success
        """
        response = await self.client.put(
            f"/v1/projects/{project_id}/disk/{disk_id}/detach"
        )
        response.raise_for_status()
        return response.json()
    
    # ========================================================================
    # Projects
    # ========================================================================
    
    async def list_projects(
        self,
        page_token: Optional[str] = None,
        page_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """List projects accessible by the current user.
        
        Args:
            page_token: Page token for pagination
            page_size: Results per page
            
        Returns:
            Projects list with pagination info
        """
        params = {}
        if page_token:
            params["pageToken"] = page_token
        if page_size is not None:
            params["pageSize"] = page_size
        
        response = await self.client.get(
            "/v1/projects",
            params=params,
        )
        response.raise_for_status()
        return response.json()
    
    async def get_project(self, project_id: str) -> Dict[str, Any]:
        """Get details of a specific project.
        
        Args:
            project_id: Project ID
            
        Returns:
            Project details
        """
        response = await self.client.get(f"/v1/projects/{project_id}")
        response.raise_for_status()
        return response.json()
    
    async def create_project(
        self,
        project_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a new project.
        
        Args:
            project_data: Project configuration
            
        Returns:
            Created project details
        """
        response = await self.client.post(
            "/v1/projects",
            json=project_data,
        )
        response.raise_for_status()
        return response.json()
    
    async def delete_project(self, project_id: str) -> Dict[str, Any]:
        """Delete a project.
        
        Args:
            project_id: Project ID to delete
            
        Returns:
            Empty response on success
        """
        response = await self.client.delete(f"/v1/projects/{project_id}")
        response.raise_for_status()
        return response.json()
    
    # ========================================================================
    # Authentication / Users
    # ========================================================================
    
    async def whoami(self) -> Dict[str, Any]:
        """Get details of the current authenticated user.
        
        Returns:
            User details including email, ID, and account information
        """
        response = await self.client.get("/v1/auth")
        response.raise_for_status()
        return response.json()
    
    # ========================================================================
    # SSH Keys
    # ========================================================================
    
    async def list_ssh_keys(
        self,
        page_number: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List SSH keys of the current user.
        
        Args:
            page_number: Page number for pagination
            page_size: Results per page
            
        Returns:
            List of SSH key dictionaries
        """
        params = {}
        if page_number is not None:
            params["pageNumber"] = page_number
        if page_size is not None:
            params["pageSize"] = page_size
        
        response = await self.client.get(
            "/v1/ssh-keys",
            params=params,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("sshKeys", [])
    
    async def create_ssh_key(
        self,
        public_key: str,
    ) -> Dict[str, Any]:
        """Create an SSH key for accessing machines.
        
        Args:
            public_key: SSH public key
            
        Returns:
            Created SSH key details
        """
        response = await self.client.post(
            "/v1/ssh-keys",
            json={"publicKey": public_key},
        )
        response.raise_for_status()
        return response.json()
    
    async def delete_ssh_key(self, ssh_key_id: str) -> Dict[str, Any]:
        """Delete an SSH key.
        
        Args:
            ssh_key_id: SSH key ID to delete
            
        Returns:
            Empty response on success
        """
        response = await self.client.delete(f"/v1/ssh-keys/{ssh_key_id}")
        response.raise_for_status()
        return response.json()
    
    # ========================================================================
    # Security Groups
    # ========================================================================
    
    async def list_security_groups(
        self,
        project_id: str,
        data_center_id: Optional[str] = None,
        page_number: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List security groups in a project.
        
        Args:
            project_id: Project ID
            data_center_id: Optional data center filter
            page_number: Page number for pagination
            page_size: Results per page
            
        Returns:
            List of security group dictionaries
        """
        params = {}
        if data_center_id:
            params["dataCenterId"] = data_center_id
        if page_number is not None:
            params["pageNumber"] = page_number
        if page_size is not None:
            params["pageSize"] = page_size
        
        response = await self.client.get(
            f"/v1/projects/{project_id}/security-groups",
            params=params,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("securityGroups", [])
    
    # ========================================================================
    # Networks
    # ========================================================================
    
    async def list_networks(
        self,
        project_id: str,
        page_number: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List all virtual networks in a project.
        
        Args:
            project_id: Project ID
            page_number: Page number for pagination
            page_size: Results per page
            
        Returns:
            List of network dictionaries
        """
        params = {}
        if page_number is not None:
            params["pageNumber"] = page_number
        if page_size is not None:
            params["pageSize"] = page_size
        
        response = await self.client.get(
            f"/v1/projects/{project_id}/networks",
            params=params,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("networks", [])
    
    async def create_network(
        self,
        project_id: str,
        network_id: str,
        data_center_id: str,
        ip_range: str,
    ) -> Dict[str, Any]:
        """Create a new virtual network.
        
        Args:
            project_id: Project ID
            network_id: Unique network ID
            data_center_id: Data center ID
            ip_range: IP range for the network (CIDR notation)
            
        Returns:
            Created network details
        """
        body = {
            "id": network_id,
            "dataCenterId": data_center_id,
            "ipRange": ip_range,
        }
        
        response = await self.client.post(
            f"/v1/projects/{project_id}/networks",
            json=body,
        )
        response.raise_for_status()
        return response.json()
    
    async def delete_network(
        self,
        project_id: str,
        network_id: str,
    ) -> Dict[str, Any]:
        """Delete a virtual network.
        
        Args:
            project_id: Project ID
            network_id: Network ID to delete
            
        Returns:
            Empty response on success
        """
        response = await self.client.delete(
            f"/v1/projects/{project_id}/networks/{network_id}"
        )
        response.raise_for_status()
        return response.json()
    
    # ========================================================================
    # Clusters
    # ========================================================================
    
    async def list_clusters(
        self,
        project_id: str,
        page_number: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """List clusters within a project.
        
        Clusters are high-performance computing environments that can be used
        to run large-scale parallel and distributed applications.
        
        Args:
            project_id: Project ID to list clusters from
            page_number: Page number for pagination (min 1)
            page_size: Results per page for pagination (min 1, max 100)
            
        Returns:
            Dict with 'clusters', 'totalCount', 'pageNumber', 'pageSize'
        """
        params = {}
        if page_number is not None:
            params["pageNumber"] = page_number
        if page_size is not None:
            params["pageSize"] = page_size
        
        response = await self.client.get(
            f"/v1/projects/{project_id}/clusters",
            params=params,
        )
        response.raise_for_status()
        return response.json()
    
    # ========================================================================
    # Bare Metal Machines
    # ========================================================================
    
    async def list_machines(
        self,
        project_id: str,
        page_number: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """List bare-metal machines within a project.
        
        Bare-metal machines are dedicated physical servers for high-performance
        computing, offering full control and isolation from other users.
        
        Args:
            project_id: Project ID to list machines from
            page_number: Page number for pagination (min 1)
            page_size: Results per page for pagination (min 1, max 100)
            
        Returns:
            Dict with 'machines', 'totalCount', 'pageNumber', 'pageSize'
        """
        params = {}
        if page_number is not None:
            params["pageNumber"] = page_number
        if page_size is not None:
            params["pageSize"] = page_size
        
        response = await self.client.get(
            f"/v1/projects/{project_id}/machines",
            params=params,
        )
        response.raise_for_status()
        return response.json()
    
    async def get_cluster(
        self,
        project_id: str,
        cluster_id: str,
    ) -> Dict[str, Any]:
        """Get details of a specific cluster.
        
        Args:
            project_id: Project ID
            cluster_id: Cluster ID
            
        Returns:
            Cluster details
        """
        response = await self.client.get(
            f"/v1/projects/{project_id}/clusters/{cluster_id}"
        )
        response.raise_for_status()
        return response.json()
    
    async def create_cluster(
        self,
        project_id: str,
        cluster_id: str,
        data_center_id: str,
        machine_type_id: str,
        machine_count: int,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create a new cluster.
        
        Args:
            project_id: Project ID
            cluster_id: Unique cluster identifier
            data_center_id: Data center ID
            machine_type_id: Machine type ID
            machine_count: Number of machines in the cluster
            **kwargs: Additional cluster configuration (commitmentTerm, customSshKeys, etc.)
            
        Returns:
            Created cluster details
        """
        body = {
            "id": cluster_id,
            "dataCenterId": data_center_id,
            "machineTypeId": machine_type_id,
            "machineCount": machine_count,
        }
        body.update(kwargs)
        
        response = await self.client.post(
            f"/v1/projects/{project_id}/clusters",
            json=body,
        )
        response.raise_for_status()
        return response.json()
    
    async def update_cluster(
        self,
        project_id: str,
        cluster_id: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Update a cluster.
        
        Args:
            project_id: Project ID
            cluster_id: Cluster ID
            **kwargs: Fields to update (machineCount, customSshKeys, etc.)
            
        Returns:
            Updated cluster details
        """
        response = await self.client.patch(
            f"/v1/projects/{project_id}/clusters/{cluster_id}",
            json=kwargs,
        )
        response.raise_for_status()
        return response.json()
    
    async def delete_cluster(
        self,
        project_id: str,
        cluster_id: str,
    ) -> Dict[str, Any]:
        """Delete a cluster. All data on machines will be lost.
        
        Args:
            project_id: Project ID
            cluster_id: Cluster ID to delete
            
        Returns:
            Empty response on success
        """
        response = await self.client.delete(
            f"/v1/projects/{project_id}/clusters/{cluster_id}"
        )
        response.raise_for_status()
        return response.json()
    
    async def get_machine(
        self,
        project_id: str,
        machine_id: str,
    ) -> Dict[str, Any]:
        """Get details of a bare-metal machine.
        
        Args:
            project_id: Project ID
            machine_id: Machine ID
            
        Returns:
            Machine details
        """
        response = await self.client.get(
            f"/v1/projects/{project_id}/machines/{machine_id}"
        )
        response.raise_for_status()
        return response.json()
    
    async def create_machine(
        self,
        project_id: str,
        machine_id: str,
        data_center_id: str,
        machine_type_id: str,
        os: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create a new bare-metal machine.
        
        Args:
            project_id: Project ID
            machine_id: Unique machine identifier
            data_center_id: Data center ID
            machine_type_id: Machine type ID
            os: Operating system to install
            **kwargs: Additional configuration (commitmentTerm, customSshKeys, etc.)
            
        Returns:
            Created machine details
        """
        body = {
            "id": machine_id,
            "dataCenterId": data_center_id,
            "machineTypeId": machine_type_id,
            "os": os,
        }
        body.update(kwargs)
        
        response = await self.client.post(
            f"/v1/projects/{project_id}/machines",
            json=body,
        )
        response.raise_for_status()
        return response.json()
    
    async def update_machine(
        self,
        project_id: str,
        machine_id: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Update a bare-metal machine.
        
        Args:
            project_id: Project ID
            machine_id: Machine ID
            **kwargs: Fields to update
            
        Returns:
            Updated machine details
        """
        response = await self.client.patch(
            f"/v1/projects/{project_id}/machines/{machine_id}",
            json=kwargs,
        )
        response.raise_for_status()
        return response.json()
    
    async def delete_machine(
        self,
        project_id: str,
        machine_id: str,
    ) -> Dict[str, Any]:
        """Delete a bare-metal machine.
        
        Machines in a commitment term cannot be deleted.
        
        Args:
            project_id: Project ID
            machine_id: Machine ID to delete
            
        Returns:
            Empty response on success
        """
        response = await self.client.delete(
            f"/v1/projects/{project_id}/machines/{machine_id}"
        )
        response.raise_for_status()
        return response.json()
    
    async def update_vm(
        self,
        project_id: str,
        vm_id: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Update a virtual machine.
        
        Args:
            project_id: Project ID
            vm_id: VM ID
            **kwargs: Fields to update
            
        Returns:
            Updated VM details
        """
        response = await self.client.patch(
            f"/v1/projects/{project_id}/vms/{vm_id}",
            json=kwargs,
        )
        response.raise_for_status()
        return response.json()
    
    async def get_network(
        self,
        project_id: str,
        network_id: str,
    ) -> Dict[str, Any]:
        """Get details of a virtual network.
        
        Args:
            project_id: Project ID
            network_id: Network ID
            
        Returns:
            Network details
        """
        response = await self.client.get(
            f"/v1/projects/{project_id}/networks/{network_id}"
        )
        response.raise_for_status()
        return response.json()
    
    async def update_network(
        self,
        project_id: str,
        network_id: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Update a virtual network.
        
        Args:
            project_id: Project ID
            network_id: Network ID
            **kwargs: Fields to update
            
        Returns:
            Updated network details
        """
        response = await self.client.patch(
            f"/v1/projects/{project_id}/networks/{network_id}",
            json=kwargs,
        )
        response.raise_for_status()
        return response.json()
    
    async def get_security_group(
        self,
        project_id: str,
        security_group_id: str,
    ) -> Dict[str, Any]:
        """Get details of a security group.
        
        Args:
            project_id: Project ID
            security_group_id: Security group ID
            
        Returns:
            Security group details
        """
        response = await self.client.get(
            f"/v1/projects/{project_id}/security-groups/{security_group_id}"
        )
        response.raise_for_status()
        return response.json()
    
    async def update_security_group(
        self,
        project_id: str,
        security_group_id: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """Update a security group.
        
        Args:
            project_id: Project ID
            security_group_id: Security group ID
            **kwargs: Fields to update
            
        Returns:
            Updated security group details
        """
        response = await self.client.patch(
            f"/v1/projects/{project_id}/security-groups/{security_group_id}",
            json=kwargs,
        )
        response.raise_for_status()
        return response.json()
    
    async def update_project(
        self,
        project_id: str,
        billing_account_id: str,
    ) -> Dict[str, Any]:
        """Update a project.
        
        Args:
            project_id: Project ID
            billing_account_id: New billing account ID
            
        Returns:
            Updated project details
        """
        body = {
            "billingAccountId": billing_account_id,
        }
        response = await self.client.patch(
            f"/v1/projects/{project_id}",
            json=body,
        )
        response.raise_for_status()
        return response.json()
    
    async def get_private_vm_image(
        self,
        project_id: str,
        image_id: str,
    ) -> Dict[str, Any]:
        """Get details of a private VM image.
        
        Args:
            project_id: Project ID
            image_id: Image ID
            
        Returns:
            Image details
        """
        response = await self.client.get(
            f"/v1/projects/{project_id}/images/{image_id}"
        )
        response.raise_for_status()
        return response.json()
    
    async def get_data_center(
        self,
        data_center_id: str,
    ) -> Dict[str, Any]:
        """Get details of a specific data center.
        
        Note: This is a helper method that filters list_vm_data_centers results.
        
        Args:
            data_center_id: Data center ID
            
        Returns:
            Data center details
        """
        data_centers = await self.list_vm_data_centers()
        for dc in data_centers:
            if dc.get("id") == data_center_id:
                return dc
        raise ValueError(f"Data center '{data_center_id}' not found")


# Singleton instance factory
_sdk_instance: Optional[CudoComputeSDK] = None


def get_cudo_compute_sdk(api_key: str) -> CudoComputeSDK:
    """Get or create a CudoComputeSDK singleton instance.
    
    Args:
        api_key: Cudo Compute API key
        
    Returns:
        CudoComputeSDK instance
    """
    global _sdk_instance
    if _sdk_instance is None:
        _sdk_instance = CudoComputeSDK(api_key)
    return _sdk_instance


__all__ = [
    "CudoComputeSDK",
    "get_cudo_compute_sdk",
]
