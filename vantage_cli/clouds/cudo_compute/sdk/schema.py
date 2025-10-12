"""Schema definitions for Cudo Compute SDK."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================================
# Common/Shared Models
# ============================================================================


class Price(BaseModel):
    """Price value."""

    value: str


class Location(BaseModel):
    """Geographic location."""

    latitude: Optional[float] = None
    longitude: Optional[float] = None


class InstalledPackage(BaseModel):
    """Installed package information."""

    name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None


# ============================================================================
# Project Models
# ============================================================================


class Project(BaseModel):
    """Cudo Compute project."""

    id: str
    billing_account_id: Optional[str] = Field(None, alias="billingAccountId")
    resource_count: Optional[int] = Field(None, alias="resourceCount")
    create_by: Optional[str] = Field(None, alias="createBy")

    class Config:
        populate_by_name = True


class ProjectPermission(BaseModel):
    """Project user permission."""

    user_id: Optional[str] = Field(None, alias="userId")
    user_email: Optional[str] = Field(None, alias="userEmail")
    user_picture: Optional[str] = Field(None, alias="userPicture")
    role: Optional[str] = None
    permission_role: Optional[str] = Field(None, alias="permissionRole")

    class Config:
        populate_by_name = True


# ============================================================================
# SSH Key Models
# ============================================================================


class SSHKey(BaseModel):
    """SSH key."""

    id: str
    create_time: Optional[str] = Field(None, alias="createTime")
    public_key: Optional[str] = Field(None, alias="publicKey")
    fingerprint: Optional[str] = None
    type: Optional[str] = None
    comment: Optional[str] = None

    class Config:
        populate_by_name = True


# ============================================================================
# Disk Models
# ============================================================================


class Disk(BaseModel):
    """Storage disk."""

    id: str
    project_id: Optional[str] = Field(None, alias="projectId")
    data_center_id: Optional[str] = Field(None, alias="dataCenterId")
    vm_id: Optional[str] = Field(None, alias="vmId")
    size_gib: Optional[int] = Field(None, alias="sizeGib")
    storage_class: Optional[str] = Field(None, alias="storageClass")
    disk_type: Optional[str] = Field(None, alias="diskType")
    public_image_id: Optional[str] = Field(None, alias="publicImageId")
    private_image_id: Optional[str] = Field(None, alias="privateImageId")
    create_time: Optional[str] = Field(None, alias="createTime")
    disk_state: Optional[str] = Field(None, alias="diskState")

    class Config:
        populate_by_name = True


# ============================================================================
# Image Models
# ============================================================================


class Image(BaseModel):
    """VM or machine image."""

    id: str
    name: Optional[str] = None
    description: Optional[str] = None
    display_name: Optional[str] = Field(None, alias="displayName")
    platform: Optional[str] = None
    size_gib: Optional[int] = Field(None, alias="sizeGib")
    installed_packages: Optional[List[InstalledPackage]] = Field(
        None, alias="installedPackages"
    )

    class Config:
        populate_by_name = True


# ============================================================================
# Network Models
# ============================================================================


class Network(BaseModel):
    """Virtual network."""

    project_id: Optional[str] = Field(None, alias="projectId")
    id: str
    data_center_id: Optional[str] = Field(None, alias="dataCenterId")
    ip_range: Optional[str] = Field(None, alias="ipRange")
    gateway: Optional[str] = None
    price_hr: Optional[Price] = Field(None, alias="priceHr")
    external_ip_address: Optional[str] = Field(None, alias="externalIpAddress")
    internal_ip_address: Optional[str] = Field(None, alias="internalIpAddress")
    vm_state: Optional[str] = Field(None, alias="vmState")
    create_time: Optional[str] = Field(None, alias="createTime")
    state: Optional[str] = None

    class Config:
        populate_by_name = True


# ============================================================================
# Security Group Models
# ============================================================================


class SecurityGroupRule(BaseModel):
    """Security group rule."""

    id: Optional[str] = None
    protocol: Optional[str] = None
    ports: Optional[str] = None
    rule_type: Optional[str] = Field(None, alias="ruleType")
    ip_range_cidr: Optional[str] = Field(None, alias="ipRangeCidr")
    icmp_type: Optional[str] = Field(None, alias="icmpType")

    class Config:
        populate_by_name = True


class SecurityGroup(BaseModel):
    """Security group."""

    project_id: Optional[str] = Field(None, alias="projectId")
    data_center_id: Optional[str] = Field(None, alias="dataCenterId")
    id: str
    description: Optional[str] = None
    rules: Optional[List[SecurityGroupRule]] = None

    class Config:
        populate_by_name = True


# ============================================================================
# VM Machine Type Models
# ============================================================================


class VMMachineTypePrice(BaseModel):
    """VM machine type pricing for commitment terms."""

    vcpu_price_hr: Optional[Price] = Field(None, alias="vcpuPriceHr")
    memory_gib_price_hr: Optional[Price] = Field(None, alias="memoryGibPriceHr")
    gpu_price_hr: Optional[Price] = Field(None, alias="gpuPriceHr")
    commitment_term: Optional[str] = Field(None, alias="commitmentTerm")

    class Config:
        populate_by_name = True


class VMMachineType(BaseModel):
    """VM machine type configuration and pricing."""

    data_center_id: Optional[str] = Field(None, alias="dataCenterId")
    machine_type: Optional[str] = Field(None, alias="machineType")
    cpu_model: Optional[str] = Field(None, alias="cpuModel")
    gpu_model: Optional[str] = Field(None, alias="gpuModel")
    gpu_model_id: Optional[str] = Field(None, alias="gpuModelId")
    min_vcpu_per_memory_gib: Optional[float] = Field(None, alias="minVcpuPerMemoryGib")
    max_vcpu_per_memory_gib: Optional[float] = Field(None, alias="maxVcpuPerMemoryGib")
    min_vcpu_per_gpu: Optional[float] = Field(None, alias="minVcpuPerGpu")
    max_vcpu_per_gpu: Optional[Any] = Field(None, alias="maxVcpuPerGpu")  # Can be "Infinity"
    vcpu_price_hr: Optional[Price] = Field(None, alias="vcpuPriceHr")
    memory_gib_price_hr: Optional[Price] = Field(None, alias="memoryGibPriceHr")
    gpu_price_hr: Optional[Price] = Field(None, alias="gpuPriceHr")
    min_storage_gib_price_hr: Optional[Price] = Field(None, alias="minStorageGibPriceHr")
    ipv4_price_hr: Optional[Price] = Field(None, alias="ipv4PriceHr")
    renewable_energy: Optional[bool] = Field(None, alias="renewableEnergy")
    max_vcpu_free: Optional[int] = Field(None, alias="maxVcpuFree")
    total_vcpu_free: Optional[int] = Field(None, alias="totalVcpuFree")
    max_memory_gib_free: Optional[int] = Field(None, alias="maxMemoryGibFree")
    total_memory_gib_free: Optional[int] = Field(None, alias="totalMemoryGibFree")
    max_gpu_free: Optional[int] = Field(None, alias="maxGpuFree")
    total_gpu_free: Optional[int] = Field(None, alias="totalGpuFree")
    max_storage_gib_free: Optional[int] = Field(None, alias="maxStorageGibFree")
    total_storage_gib_free: Optional[int] = Field(None, alias="totalStorageGibFree")
    min_vcpu: Optional[float] = Field(None, alias="minVcpu")
    min_memory_gib: Optional[float] = Field(None, alias="minMemoryGib")
    prices: Optional[List[VMMachineTypePrice]] = None

    class Config:
        populate_by_name = True


# ============================================================================
# Bare-Metal Machine Type Models
# ============================================================================


class MachineTypePrice(BaseModel):
    """Bare-metal machine type pricing."""

    data_center_id: Optional[str] = Field(None, alias="dataCenterId")
    machine_type_id: Optional[str] = Field(None, alias="machineTypeId")
    commitment_term: Optional[str] = Field(None, alias="commitmentTerm")
    price_hr: Optional[Price] = Field(None, alias="priceHr")
    ipv4_price_hr: Optional[Price] = Field(None, alias="ipv4PriceHr")

    class Config:
        populate_by_name = True


class MachineType(BaseModel):
    """Bare-metal machine type."""

    data_center_id: Optional[str] = Field(None, alias="dataCenterId")
    id: str
    architecture: Optional[str] = None
    cpu_cores: Optional[int] = Field(None, alias="cpuCores")
    cpu_speed_mhz: Optional[int] = Field(None, alias="cpuSpeedMhz")
    cpu_model: Optional[str] = Field(None, alias="cpuModel")
    memory_gib: Optional[int] = Field(None, alias="memoryGib")
    disks: Optional[int] = None
    disk_size_gib: Optional[int] = Field(None, alias="diskSizeGib")
    gpus: Optional[int] = None
    gpu_model_id: Optional[str] = Field(None, alias="gpuModelId")
    prices: Optional[List[MachineTypePrice]] = None
    machines_free: Optional[int] = Field(None, alias="machinesFree")
    network_type: Optional[str] = Field(None, alias="networkType")

    class Config:
        populate_by_name = True


# ============================================================================
# Machine (Bare-Metal) Models
# ============================================================================


class Machine(BaseModel):
    """Bare-metal machine instance."""

    data_center_id: Optional[str] = Field(None, alias="dataCenterId")
    id: str
    machine_type_id: Optional[str] = Field(None, alias="machineTypeId")
    architecture: Optional[str] = None
    cpu_cores: Optional[int] = Field(None, alias="cpuCores")
    cpu_speed_mhz: Optional[int] = Field(None, alias="cpuSpeedMhz")
    cpu_model: Optional[str] = Field(None, alias="cpuModel")
    memory_gib: Optional[int] = Field(None, alias="memoryGib")
    disks: Optional[int] = None
    disk_size_gib: Optional[int] = Field(None, alias="diskSizeGib")
    gpus: Optional[int] = None
    gpu_model_id: Optional[str] = Field(None, alias="gpuModelId")
    state: Optional[str] = None
    power_state: Optional[str] = Field(None, alias="powerState")
    os: Optional[str] = None
    hostname: Optional[str] = None
    external_ip_addresses: Optional[List[str]] = Field(None, alias="externalIpAddresses")
    project_id: Optional[str] = Field(None, alias="projectId")
    create_time: Optional[str] = Field(None, alias="createTime")
    create_by: Optional[str] = Field(None, alias="createBy")
    commitment_term: Optional[str] = Field(None, alias="commitmentTerm")
    price_hr: Optional[Price] = Field(None, alias="priceHr")
    user_data: Optional[str] = Field(None, alias="userData")
    ssh_key_source: Optional[str] = Field(None, alias="sshKeySource")
    custom_ssh_keys: Optional[List[str]] = Field(None, alias="customSshKeys")
    start_script: Optional[str] = Field(None, alias="startScript")

    class Config:
        populate_by_name = True


# ============================================================================
# VM Models
# ============================================================================


class VMNic(BaseModel):
    """VM network interface."""

    network_id: Optional[str] = Field(None, alias="networkId")
    external_ip_address: Optional[str] = Field(None, alias="externalIpAddress")
    internal_ip_address: Optional[str] = Field(None, alias="internalIpAddress")
    network_address: Optional[str] = Field(None, alias="networkAddress")
    security_group_ids: Optional[List[str]] = Field(None, alias="securityGroupIds")

    class Config:
        populate_by_name = True


class VMPrice(BaseModel):
    """VM pricing breakdown."""

    vcpu_price_hr: Optional[Price] = Field(None, alias="vcpuPriceHr")
    total_vcpu_price_hr: Optional[Price] = Field(None, alias="totalVcpuPriceHr")
    memory_gib_price_hr: Optional[Price] = Field(None, alias="memoryGibPriceHr")
    total_memory_price_hr: Optional[Price] = Field(None, alias="totalMemoryPriceHr")
    gpu_price_hr: Optional[Price] = Field(None, alias="gpuPriceHr")
    total_gpu_price_hr: Optional[Price] = Field(None, alias="totalGpuPriceHr")
    storage_gib_price_hr: Optional[Price] = Field(None, alias="storageGibPriceHr")
    total_storage_price_hr: Optional[Price] = Field(None, alias="totalStoragePriceHr")
    ipv4_address_price_hr: Optional[Price] = Field(None, alias="ipv4AddressPriceHr")
    total_price_hr: Optional[Price] = Field(None, alias="totalPriceHr")

    class Config:
        populate_by_name = True


class VM(BaseModel):
    """Virtual machine instance."""

    datacenter_id: Optional[str] = Field(None, alias="datacenterId")
    machine_type: Optional[str] = Field(None, alias="machineType")
    id: str
    external_ip_address: Optional[str] = Field(None, alias="externalIpAddress")
    internal_ip_address: Optional[str] = Field(None, alias="internalIpAddress")
    public_ip_address: Optional[str] = Field(None, alias="publicIpAddress")
    memory: Optional[int] = None
    cpu_model: Optional[str] = Field(None, alias="cpuModel")
    vcpus: Optional[int] = None
    gpu_model: Optional[str] = Field(None, alias="gpuModel")
    gpu_model_id: Optional[str] = Field(None, alias="gpuModelId")
    gpu_quantity: Optional[int] = Field(None, alias="gpuQuantity")
    boot_disk_size_gib: Optional[int] = Field(None, alias="bootDiskSizeGib")
    renewable_energy: Optional[bool] = Field(None, alias="renewableEnergy")
    image_id: Optional[str] = Field(None, alias="imageId")
    public_image_id: Optional[str] = Field(None, alias="publicImageId")
    public_image_name: Optional[str] = Field(None, alias="publicImageName")
    private_image_id: Optional[str] = Field(None, alias="privateImageId")
    image_name: Optional[str] = Field(None, alias="imageName")
    create_by: Optional[str] = Field(None, alias="createBy")
    nics: Optional[List[VMNic]] = None
    rules: Optional[List[SecurityGroupRule]] = None
    security_group_ids: Optional[List[str]] = Field(None, alias="securityGroupIds")
    short_state: Optional[str] = Field(None, alias="shortState")
    boot_disk: Optional[Disk] = Field(None, alias="bootDisk")
    storage_disks: Optional[List[Disk]] = Field(None, alias="storageDisks")
    metadata: Optional[Dict[str, Any]] = None
    state: Optional[str] = None
    create_time: Optional[str] = Field(None, alias="createTime")
    expire_time: Optional[str] = Field(None, alias="expireTime")
    price: Optional[VMPrice] = None
    commitment_term: Optional[str] = Field(None, alias="commitmentTerm")
    commitment_end_time: Optional[str] = Field(None, alias="commitmentEndTime")
    ssh_key_source: Optional[str] = Field(None, alias="sshKeySource")
    authorized_ssh_keys: Optional[str] = Field(None, alias="authorizedSshKeys")
    security_groups: Optional[List[SecurityGroup]] = Field(None, alias="securityGroups")
    project_id: Optional[str] = Field(None, alias="projectId")

    class Config:
        populate_by_name = True


# ============================================================================
# Data Center Models
# ============================================================================


class DiskPoolPricing(BaseModel):
    """Data center disk pool pricing."""

    storage_class: Optional[str] = Field(None, alias="storageClass")
    disk_gib_price_hr: Optional[Price] = Field(None, alias="diskGibPriceHr")

    class Config:
        populate_by_name = True


class NetworkPricing(BaseModel):
    """Data center network pricing."""

    price_hr: Optional[Price] = Field(None, alias="priceHr")

    class Config:
        populate_by_name = True


class VMDataCenter(BaseModel):
    """VM data center."""

    id: str
    supplier_name: Optional[str] = Field(None, alias="supplierName")
    renewable_energy: Optional[bool] = Field(None, alias="renewableEnergy")
    disk_pool_pricing: Optional[List[DiskPoolPricing]] = Field(
        None, alias="diskPoolPricing"
    )
    network_pricing: Optional[List[NetworkPricing]] = Field(None, alias="networkPricing")
    network_price_hr: Optional[Price] = Field(None, alias="networkPriceHr")
    ipv4_price_hr: Optional[Price] = Field(None, alias="ipv4PriceHr")
    ipv4_free: Optional[int] = Field(None, alias="ipv4Free")
    s3_endpoint: Optional[str] = Field(None, alias="s3Endpoint")
    location: Optional[Location] = None
    object_storage_gib_price_hr: Optional[Price] = Field(
        None, alias="objectStorageGibPriceHr"
    )

    class Config:
        populate_by_name = True


class DataCenter(BaseModel):
    """Generic data center (for bare-metal or other services)."""

    id: str
    name: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    location: Optional[Location] = None

    class Config:
        populate_by_name = True


# ============================================================================
# Volume Models  
# ============================================================================


class Volume(BaseModel):
    """NFS volume."""

    id: str
    project_id: Optional[str] = Field(None, alias="projectId")
    data_center_id: Optional[str] = Field(None, alias="dataCenterId")
    size_gib: Optional[int] = Field(None, alias="sizeGib")
    state: Optional[str] = None
    create_time: Optional[str] = Field(None, alias="createTime")
    price_hr: Optional[Price] = Field(None, alias="priceHr")
    mount_point: Optional[str] = Field(None, alias="mountPoint")

    class Config:
        populate_by_name = True


# ============================================================================
# Cluster Models
# ============================================================================


class ClusterNode(BaseModel):
    """Cluster node."""

    id: Optional[str] = None
    vm_id: Optional[str] = Field(None, alias="vmId")
    role: Optional[str] = None
    state: Optional[str] = None

    class Config:
        populate_by_name = True


class Cluster(BaseModel):
    """Compute cluster."""

    id: str
    project_id: Optional[str] = Field(None, alias="projectId")
    data_center_id: Optional[str] = Field(None, alias="dataCenterId")
    cluster_type: Optional[str] = Field(None, alias="clusterType")
    state: Optional[str] = None
    create_time: Optional[str] = Field(None, alias="createTime")
    nodes: Optional[List[ClusterNode]] = None
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        populate_by_name = True

