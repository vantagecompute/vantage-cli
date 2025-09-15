"""Core module for storing pydantic schemas related to the database."""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, validator

from api.sql_app.enums import (
    CloudAccountEnum,
    ClusterProviderEnum,
    ClusterStatusEnum,
    StorageSourceEnum,
    SubscriptionTiersNames,
    SubscriptionTypesNames,
)


class ConfigModel(BaseModel):

    """Pydantic model for defining the configuration of the models."""

    class Config:
        """Pydantic model configuration."""

        orm_mode = True
        arbitrary_types_allowed = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class ClusterRow(ConfigModel):

    """Cluster table schema."""

    name: str
    description: Optional[str]
    status: ClusterStatusEnum
    client_id: str
    owner_email: Optional[str]
    provider: ClusterProviderEnum
    cloud_account_id: Optional[int]
    creation_parameters: Optional[dict[Any, Any]]
    creation_status_details: Optional[list[dict[Any, Any]]]
    slurm_cluster_config: Optional[dict[Any, Any]]
    all_partition_info: Optional[dict[Any, Any]]
    all_node_info: Optional[dict[Any, Any]]
    partitions: Optional[list[dict[Any, Any]]]
    nodes: Optional[list[dict[Any, Any]]]
    agent_health = Optional[dict[Any, Any]]


class StorageRow(ConfigModel):

    """Storage table schema."""

    id: str
    fs_id: str
    name: str
    region: str
    source: StorageSourceEnum
    owner: str
    created_at: datetime
    cloud_account_id: int
    cloud_account: Optional["CloudAccountRow"]
    mount_points: Optional[list["MountPointRow"]]


class CloudAccountRow(ConfigModel):

    """Cloud account table schema."""

    id: int
    provider: CloudAccountEnum
    name: str
    assisted_cloud_account: bool
    description: None | str = None
    attributes: dict[Any, Any]
    created_at: datetime
    updated_at: datetime


class MountPointRow(ConfigModel):

    """Mount point table schema."""

    id: int
    cluster_name: str
    storage_id: int
    client_id: str
    mount_point: str
    created_at: datetime
    status: str
    error: Optional[str]
    storage: Optional[StorageRow]
    cluster: Optional[ClusterRow]

    @validator("storage", pre=True, always=True)
    def set_storage(cls, v):  # noqa: N805
        """Set the storage field."""
        if v:
            return StorageRow.from_orm(v)

    @validator("cluster", pre=True, always=True)
    def set_cluster(cls, v):  # noqa: N805
        """Set the cluster field."""
        if v:
            return ClusterRow.from_orm(v)


class SubscriptionTypeRow(ConfigModel):

    """Subscription type table schema."""

    id: int
    name: SubscriptionTypesNames


class SubscriptionTierRow(ConfigModel):

    """Subscription tier table schema."""

    id: int
    name: SubscriptionTiersNames
    seats: None | int = None
    clusters: None | int = None
    storage_systems: None | int = None


class SubscriptionRow(ConfigModel):

    """Subscription table schema."""

    id: int
    organization_id: str
    type_id: int
    tier_id: int
    detail_data: dict[Any, Any]
    created_at: datetime
    expires_at: None | datetime = None
    is_free_trial: bool
    subscription_type: Optional[SubscriptionTypeRow]
    subscription_tier: Optional[SubscriptionTierRow]


class PendingAwsSubscriptionRow(ConfigModel):

    """Pending AWS subscription table schema."""

    id: int
    organization_id: str
    customer_aws_account_id: str
    customer_identifier: str
    product_code: str
    has_failed: bool
    created_at: datetime


class OrganizationFreeTrialsRow(ConfigModel):

    """Organization free trial table schema."""

    id: int
    organization_id: str


class PartitionRow(ConfigModel):
    """Partition table schema."""

    id: int
    cluster_name: str
    name: str
    node_type: str
    max_node_count: int
    is_default: bool


class NodeRow(ConfigModel):

    """Node table schema."""

    id: int
    cluster_name: str
    name: str
    partition_names: list[str]
    info: dict[Any, Any]
    updated_at: datetime


class PartitionInfoRow(ConfigModel):

    """Partition table schema."""

    id: int
    cluster_name: str
    name: str
    info: dict[Any, Any]
    updated_at: datetime


StorageRow.update_forward_refs()
SubscriptionRow.update_forward_refs()
