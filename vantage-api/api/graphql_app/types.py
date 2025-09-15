"""Core module for defining the GraphQL types."""
import datetime
import enum
import json
from contextlib import asynccontextmanager
from functools import cached_property
from typing import Any, AsyncGenerator, Dict, Generic, List, NewType, Optional, TypeVar, Union

import strawberry
from sqlalchemy.ext.asyncio import AsyncSession
from strawberry.fastapi import BaseContext
from strawberry.types import Info as _Info
from strawberry.types.info import RootValueType

from api.settings import SETTINGS
from api.sql_app.enums import (
    ClusterProviderEnum,
    ClusterQueueActionEnum,
    ClusterStatusEnum,
    MountPointStatusEnum,
    StorageSourceEnum,
)
from api.sql_app.models import ClusterModel, MountPointModel, StorageModel
from api.sql_app.session import create_async_session

GenericType = TypeVar("GenericType")


@strawberry.type
class DecodedToken:

    """Class to map user's information decoded from the access token."""

    email: str
    permissions: List[str]
    organization: str


class Context(BaseContext):

    """Context class to override the default context from Strawberry.

    All methods defined in here are available as awaitables in the info object. Exaple:

    async def whatever(info: Info) -> str:
        "Get user email from the token"  # pflake8 complains about triple quotes here
        return (await info.context.decoded_token).email
    """

    _token_data: DecodedToken

    @cached_property
    def token_data(self) -> DecodedToken:
        """Return the token data synchronously."""
        return self._token_data

    @cached_property
    async def decoded_token(self) -> Union[DecodedToken, None]:
        """Store the decoded token from Armasec in the context."""
        if not self.request:
            return None

        decoded_token = await SETTINGS.GUARD.lockdown()(self.request)
        organization = decoded_token.organization

        decoded_token_instance = DecodedToken(
            # empty string in email is used for the agent purposes
            email=decoded_token.email if hasattr(decoded_token, "email") else "",
            permissions=decoded_token.permissions,
            organization=organization[next(iter(organization))].get("id"),
        )

        setattr(self, "_token_data", decoded_token_instance)

        return decoded_token_instance

    @asynccontextmanager
    async def db_session(self, db: str, read_only: bool = False) -> AsyncGenerator[AsyncSession, None]:
        """Store the database session in the context."""
        session = await create_async_session(db, read_only=read_only)
        async with session() as sess:
            async with sess.begin():
                try:
                    yield sess
                except Exception as err:
                    await sess.rollback()
                    raise err
                finally:
                    await sess.close()


Info = _Info[Context, RootValueType]
SelfCluster = TypeVar("SelfCluster", bound="Cluster")
SelfStorage = TypeVar("SelfStorage", bound="Storage")


JSONScalar = strawberry.scalar(
    NewType("JSONScalar", Any),
    serialize=lambda v: v,
    parse_value=lambda v: json.loads(json.dumps(v)),
    description=(
        "The GenericScalar scalar type represents a generic"
        " GraphQL scalar value that could be: List or Object."
    ),
)


@strawberry.type
class AwsSshKeys:

    """GraphQL type for the AWS SSH Keys."""

    key_pair_names: List[str]


class DymanicTypeMixin:

    """Define common methods for the GraphQL types defined in this module."""

    @classmethod
    def from_db_model(
        cls, table: Union[ClusterModel, StorageModel, MountPointModel], extra: Optional[Dict[str, str]] = {}
    ) -> Union[SelfCluster, SelfStorage]:
        """Generate the Strawberry type from the SQLAlchemy model."""
        return cls(**table.as_dict(), **extra)

    @classmethod
    def __name__(cls) -> str:
        """Return the name of the class."""
        return cls.__name__


ClusterProvider = strawberry.enum(ClusterProviderEnum)


ClusterStatus = strawberry.enum(ClusterStatusEnum)


ClusterQueueAction = strawberry.enum(ClusterQueueActionEnum)


StorageSource = strawberry.enum(StorageSourceEnum)


@strawberry.type
class Cluster(DymanicTypeMixin):

    """GraphQL Cluster type."""

    name: str
    status: ClusterStatus
    client_id: str
    description: str
    owner_email: Optional[str] = None
    provider: ClusterProvider
    creation_parameters: Optional[JSONScalar] = None
    creation_status_details: Optional[list[JSONScalar]] = None
    cloud_account_id: Optional[int] = None
    cloud_account: Optional["CloudAccount"] = None
    mount_points: Optional[List["MountPoint"]] = None
    slurm_cluster_config: Optional["SlurmClusterConfig"] = None
    all_partition_info: Optional[JSONScalar] = None
    all_queue_info: Optional[JSONScalar] = None
    all_node_info: Optional[JSONScalar] = None
    partitions: Optional[List["ClusterPartition"]] = None
    queue: Optional[List["ClusterPartition"]] = None
    nodes: Optional[List["ClusterNode"]] = None
    agent_health_check: Optional["AgentHealthCheck"] = None
    cluster_partitions: Optional[List["Partition"]] = None
    notebook_servers: Optional[List["NotebookServer"]] = None
    cluster_queue_actions: Optional[List["ClusterQueueActions"]] = None


@strawberry.type
class SlurmClusterConfig(DymanicTypeMixin):

    """GraphQL type for the Slurm cluster configuration."""

    id: int
    cluster_name: str
    info: JSONScalar
    updated_at: datetime.datetime
    cluster: Cluster


@strawberry.type
class ClusterPartition(DymanicTypeMixin):

    """GraphQL Partition type."""

    id: int
    cluster_name: str
    name: str
    info: JSONScalar
    updated_at: datetime.datetime
    cluster: Optional[Cluster] = None


@strawberry.type
class ClusterQueue(DymanicTypeMixin):

    """GraphQL Queue type."""

    id: int
    cluster_name: str
    name: str
    info: JSONScalar
    updated_at: datetime.datetime
    cluster: Optional[Cluster] = None
    cluster_queue_actions: Optional[List["ClusterQueueActions"]] = None


@strawberry.type
class ClusterNode(DymanicTypeMixin):

    """GraphQL Partition type."""

    id: int
    cluster_name: str
    name: str
    info: JSONScalar
    partition_names: list[str]
    updated_at: datetime.datetime
    cluster: Optional[Cluster] = None


@strawberry.type
class ClusterQueueActions(DymanicTypeMixin):

    """GraphQL Cluster Queue Actions type."""

    id: int
    cluster_name: str
    queue_id: int
    action: ClusterQueueAction
    queue: Optional[ClusterQueue] = None
    cluster: Optional[Cluster] = None


@strawberry.type
class AgentHealthCheck(DymanicTypeMixin):

    """GraphQL Agent Health Check type."""

    id: int
    cluster_name: str
    interval: int
    last_reported: datetime.datetime
    cluster: Cluster


@strawberry.enum
class ClusterRegion(str, enum.Enum):

    """Available regions for creating a cluster in."""

    # US Regions
    us_east_1 = "us-east-1"
    us_east_2 = "us-east-2"
    us_west_1 = "us-west-1"
    us_west_2 = "us-west-2"

    # Africa Regions
    af_south_1 = "af-south-1"

    # Asia Pacific Regions
    ap_south_1 = "ap-south-1"
    ap_south_2 = "ap-south-2"
    ap_northeast_1 = "ap-northeast-1"
    ap_northeast_2 = "ap-northeast-2"
    ap_northeast_3 = "ap-northeast-3"
    ap_southeast_1 = "ap-southeast-1"
    ap_southeast_2 = "ap-southeast-2"
    ap_southeast_3 = "ap-southeast-3"
    ap_southeast_4 = "ap-southeast-4"
    ap_southeast_5 = "ap-southeast-5"
    ap_east_1 = "ap-east-1"

    # Canada Regions
    ca_central_1 = "ca-central-1"
    ca_west_1 = "ca-west-1"

    # Europe Regions
    eu_central_1 = "eu-central-1"
    eu_central_2 = "eu-central-2"
    eu_north_1 = "eu-north-1"
    eu_west_1 = "eu-west-1"
    eu_west_2 = "eu-west-2"
    eu_west_3 = "eu-west-3"
    eu_south_1 = "eu-south-1"
    eu_south_2 = "eu-south-2"

    # South America Regions
    sa_east_1 = "sa-east-1"

    # Middle East Regions
    me_south_1 = "me-south-1"
    me_central_1 = "me-central-1"

    # Israel Regions
    il_central_1 = "il-central-1"


@strawberry.input
class AwsKeys:

    """GraphQL AWS keys input."""

    role_arn: str
    region_name: ClusterRegion = ClusterRegion.us_west_2


@strawberry.input
class AwsNetworking:

    """GraphQL AWS networking input."""

    vpc_id: str
    head_node_subnet_id: str
    compute_node_subnet_id: Optional[str] = None


@strawberry.input
class AwsProviderAttributes:

    """GraphQL AWS provider attributes input.

    The GraphQL spec itself doesn't support enums in union types, so we have to use strings.
    The instance type values must be validated later on.
    """

    head_node_instance_type: str = "t2.large"  # the GraphQL spec doesn't support enums in union types
    key_pair: str
    networking: Optional[AwsNetworking] = None
    cloud_account_id: int
    region_name: ClusterRegion = ClusterRegion.us_west_2


@strawberry.input
class Provider:

    """GraphQL cloud provider input."""

    aws: AwsProviderAttributes


@strawberry.input
class PartitionInput:
    """GraphQL partition attributes."""

    name: str
    is_default: bool = False
    node_type: str = "t3.large"
    max_node_count: int = 10


@strawberry.input
class CreateClusterInput:

    """GraphQL create cluster input."""

    name: str
    description: str
    secret: Optional[str] = None
    provider: ClusterProvider = ClusterProvider.on_prem
    provider_attributes: Optional[Provider] = None
    partitions: Optional[List[PartitionInput]] = None


@strawberry.input
class UpdateClusterRecordInput:

    """GraphQL update cluster input."""

    name: str
    description: Optional[str] = None


@strawberry.enum
class OrderingDirection(enum.Enum):

    """The ordering direction of a supplied field. Use `asc` for ascending and `desc` for descending."""

    ASC = "asc"
    DESC = "desc"


@strawberry.enum
class ClusterOrderingFilter(enum.Enum):

    """Available ordering for the clusters."""

    name = "name"
    status = "status"
    client_id = "client_id"
    description = "description"
    provider = "provider"


@strawberry.input
class ClusterOrderingInput:

    """Define the ordering input."""

    field: ClusterOrderingFilter
    direction: OrderingDirection = OrderingDirection.ASC


@strawberry.type
class Edge(Generic[GenericType]):

    """An edge may contain additional information of the relationship."""

    node: GenericType
    cursor: str


@strawberry.type
class PageInfo:

    """Pagination context to navigate objects with cursor-based pagination.

    Instead of classic offset pagination via `page` and `limit` parameters,
    here we have a cursor of the last object and we fetch items starting from that one

    Read more at:
        - https://graphql.org/learn/pagination/#pagination-and-edges
        - https://relay.dev/graphql/connections.htm
    """

    has_next_page: bool
    has_previous_page: bool
    start_cursor: Optional[str] = None
    end_cursor: Optional[str] = None


@strawberry.type
class Connection(Generic[GenericType]):

    """Represents a paginated relationship between two entities.

    This pattern is used when the relationship itself has attributes.
    In a Facebook-based domain example, a friendship between two people
    would be a connection that might have a `friendshipStartTime`
    """

    page_info: PageInfo
    edges: List[Edge[GenericType]]
    total: int


@strawberry.type
class InvalidProviderInput:

    """GraphQL error type for invalid cluster provider input."""

    message: str = "Aws provider was selected but no attributes were provided"


@strawberry.type
class ClusterNameInUse:

    """GraphQL error type for when the cluster name is already in use."""

    message: str = "Cluster name is already in use"


@strawberry.type
class ClusterCouldNotBeDeployed:

    """GraphQL error type for when the cluster could not be deployted on AWS."""

    message: str = "Cluster could not be deployed on AWS"


@strawberry.type
class ClusterNotFound:

    """GraphQL error type for when the cluster could not be found."""

    message: str = "Cluster could not be found."


@strawberry.type
class ClusterDeleted:

    """GraphQL error type for when the cluster has been deleted."""

    message: str = "Cluster has been deleted."


@strawberry.type
class UnexpectedBehavior:

    """GraphQL error type for when a unexpected behavior happens."""

    message: str = "Unexpected behavior"


@strawberry.type
class ParameterValidationError:

    """GraphQL error type for when a parameter validation fails."""

    message: str


@strawberry.enum
class StorageOrderingFilter(enum.Enum):

    """Available ordering for the storages."""

    name = "name"
    fs_id = "fs_id"
    source = "source"


MountPointStatus = strawberry.enum(
    enum.Enum("MountPointStatus", [(x.name, x.value) for x in MountPointStatusEnum])
)


@strawberry.input
class StorageOrderingInput:

    """Define the ordering input."""

    field: StorageOrderingFilter
    direction: OrderingDirection = OrderingDirection.ASC


@strawberry.input
class CreateStorageInput:

    """Defining create storage input."""

    fs_id: Optional[str] = None
    name: str
    region: ClusterRegion = ClusterRegion.us_west_2
    source: StorageSource = StorageSource.vantage
    cloud_account_id: int


@strawberry.type
class StorageDeleted:

    """GraphQL type for when the storage has been deleted."""

    message: str = "Storage has been deleted"


@strawberry.type
class MountPoint(DymanicTypeMixin):

    """GraphQL Mount point type."""

    id: int
    cluster_name: str
    client_id: str
    storage_id: int
    mount_point: str
    error: Union[str, None] = None
    status: MountPointStatus
    created_at: datetime.datetime
    storage: "Storage"
    cluster: "Cluster"


@strawberry.type
class CloudAccount(DymanicTypeMixin):

    """GraphQL Cloud Account type."""

    id: int
    provider: str
    name: str
    assisted_cloud_account: bool
    description: Optional[str]
    attributes: JSONScalar
    created_at: datetime.datetime
    updated_at: datetime.datetime


@strawberry.type
class Storage(DymanicTypeMixin):

    """GraphQL Storage type."""

    id: int
    fs_id: str
    name: str
    region: str
    source: StorageSource
    owner: str
    created_at: datetime.datetime
    cloud_account_id: int
    mount_points: Optional[List["MountPoint"]]
    cloud_account: Optional[CloudAccount]


@strawberry.type
class Partition(DymanicTypeMixin):
    """GraphQL Partition type."""

    id: int
    name: str
    cluster_name: str
    max_node_count: int
    node_type: str
    is_default: bool
    cluster: Optional[Cluster] = None
    nodes_info: Optional[List[ClusterNode]] = None
    partition_infos: Optional[ClusterPartition] = None


@strawberry.type
class DuplicatedStorageId:

    """GraphQL error type for when the fsid is already in use."""

    message: str = "Duplicated storage fsId"


@strawberry.type
class DuplicatedStorageName:

    """GraphQL error type for when the Storage name is already in use."""

    message: str = "Storage name is already in use"


@strawberry.type
class StorageNotFound:

    """GraphQL error type for when the Storage could not be found."""

    message: str = "Either there's no storage with supplied ID or it belongs to a different owner"


@strawberry.type
class InvalidInput:

    """GraphQL error type for when the input is a valid type but not valid after business logic."""

    message: str


@strawberry.type
class MissingAwsPermissions:

    """GraphQL error type for when the supplied role does not have the required permissions."""

    message: str


@strawberry.type
class FileSystemMisconfigured:

    """GraphQL error type for when the filesystem is misconfigured, i.e. it isn't tagged correctly."""

    message: str


@strawberry.input
class MountStorageInput:

    """GraphQL Input Type for mount storage into a cluster."""

    fs_id: str
    cluster_name: str
    region: ClusterRegion
    path: str


@strawberry.input
class UnmountStorageInput:

    """GraphQL Input Type for unmount storage from a cluster."""

    storage_id: int
    cluster_name: str


@strawberry.type
class StorageUnmounted:

    """GraphQL type for when the storage has been unmounted."""

    message: str = "Storage has been unmounted"


@strawberry.type
class StorageUnmounting:

    """GraphQL type for when the storage is being unmounted."""

    message: str = "Storage is being unmounted"


@strawberry.input
class CheckMountPointInput:

    """GraphQL type for the route to check mount point is available."""

    path: str
    cluster_name: str
    region: ClusterRegion
    cloud_account_id: int


@strawberry.type
class MountPointCheck:

    """GraphQL type for when is checking the if the mount point is valid."""

    is_available: bool


@strawberry.type
class DuplicatedMountPoint:

    """GraphQL type for when the storage already is mounted."""

    message: str = "The storage is already mounted in the requested cluster"


@strawberry.enum
class ClusterAvailableForDeletionReason(enum.Enum):

    """Reasons why a cluster is not available for deletion."""

    cluster_has_mount_points = "The cluster has at least one mount point attached."
    cluster_has_compute_nodes = "The cluster has at least one compute node up and running."
    unknown_error = "Unknown reason for why the cluster cannot be deleted. Contact support."


@strawberry.type
class ClusterAvailableForDeletion:

    """GraphQL type for checking if the cluster is available for deletion.

    *is_available* is a boolean that indicates if the cluster is available for deletion.
    """

    is_available: bool
    reason: ClusterAvailableForDeletionReason | None = None


@strawberry.type
class CloudAccountNotFound:

    """GraphQL type for when the cloud account could not be found."""

    message: str = "Cloud account could not be found"


@strawberry.type
class AwsNodeTypes(DymanicTypeMixin):

    """GraphQL type for AWS node types."""

    id: int
    instance_type: str
    aws_region: str
    cpu_manufacturer: str
    cpu_name: str
    cpu_arch: str
    num_cpus: int
    memory: int
    gpu_manufacturer: Optional[str] = None
    gpu_name: Optional[str] = None
    num_gpus: int
    price_per_hour: float


@strawberry.type
class UploadSlurmConfigSuccess:

    """GraphQL type for when the slurm config has been uploaded successfully."""

    message: str = "Slurm config uploaded successfully"


@strawberry.type
class UploadSlurmPartitionsSuccess:

    """GraphQL type for when the slurm partitions has been uploaded successfully."""

    message: str = "Slurm partitions uploaded successfully"


@strawberry.type
class UploadSlurmQueueSuccess:

    """GraphQL type for when the slurm queue has been uploaded successfully."""

    message: str = "Slurm queue uploaded successfully"


@strawberry.type
class UploadSlurmNodesSuccess:

    """GraphQL type for when the slurm nodes has been uploaded successfully."""

    message: str = "Slurm nodes uploaded successfully"


@strawberry.enum
class AwsNodesOrderingFilter(enum.Enum):

    """Available ordering for the aws nodes."""

    instance_type = "instance_type"
    aws_region = "aws_region"
    cpu_manufacturer = "cpu_manufacturer"
    cpu_name = "cpu_name"
    cpu_arch = "cpu_arch"
    num_cpus = "num_cpus"
    memory = "memory"
    gpu_manufacturer = "gpu_manufacturer"
    gpu_name = "gpu_name"
    num_gpus = "num_gpus"
    price_per_hour = "price_per_hour"


@strawberry.input
class AwsNodesOrderingInput:

    """Define the ordering input."""

    field: AwsNodesOrderingFilter
    direction: OrderingDirection = OrderingDirection.ASC


@strawberry.type
class AwsNodesFilters(DymanicTypeMixin):

    """GraphQL type for AWS node filters."""

    filter_name: str
    filter_values: list[str]


@strawberry.type
class AwsRegionsDescribed:

    """GraphQL type for the enabled AWS regions."""

    enabled_regions: list[ClusterRegion]
    disabled_regions: list[ClusterRegion]


@strawberry.input
class UpdatePartitionInput:
    """GraphQL update partition input."""

    partition_name: str
    cluster_name: str
    new_partition_name: Optional[str]
    max_node_count: Optional[int]
    node_type: Optional[str]


@strawberry.input
class CreatePartitionInput:
    """GraphQL create partition input."""

    name: str
    cluster_name: str
    max_node_count: Optional[int]
    node_type: Optional[str]


@strawberry.type
class PartitionDeleted:
    """GraphQL type for when the partition has been deleted."""

    message: str = "Partition has been deleted."


@strawberry.type
class PartitionNotFound:

    """GraphQL error type for when the partition could not be found."""

    message: str = "Cluster Partition not be found."


@strawberry.enum
class MemoryUnit(enum.Enum):

    """Available memory units for the notebook servers."""

    K = "K"
    M = "M"
    G = "G"
    T = "T"


@strawberry.input
class CreateNotebookInput:

    """GraphQL notebook srever input."""

    name: str
    cluster_name: str
    partition_name: str
    cpu_cores: Optional[int] = None
    memory: Optional[float] = None
    memory_unit: Optional[MemoryUnit] = MemoryUnit.M
    gpus: Optional[int] = None


@strawberry.enum
class NotebookServerOrderingFilter(enum.Enum):

    """Available ordering for the notebook servers."""

    name = "name"
    cluster_name = "cluster_name"
    partition = "partition"


@strawberry.input
class NotebookServerOrderingInput:

    """Define the ordering input for notebook servers."""

    field: NotebookServerOrderingFilter
    direction: OrderingDirection = OrderingDirection.ASC


@strawberry.type
class NotebookServer(DymanicTypeMixin):

    """GraphQL Storage type."""

    id: int
    partition: str
    name: str
    cluster_name: str
    owner: str
    server_url: str
    slurm_job_id: Optional[int] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    cluster: Cluster


@strawberry.type
class NotebookServerAlreadyExists:

    """GraphQL error type for when the notebook server already exists."""

    message: str = "Notebook Server already exists with the given name."


@strawberry.type
class NotebookServerNotFound:

    """GraphQL error type for when the notebook server was not found."""

    message: str = "Notebook Server not found."


@strawberry.type
class NotebookServerDeleted:
    """GraphQL type for when the notebook server has been deleted."""

    message: str = "Notebook Server has been deleted."


@strawberry.type
class NotebookServerProgress:
    """GraphQL type for the notebook server progress."""

    ready: bool = False


@strawberry.type
class JupyterHubStatus:
    """GraphQL type for the jupyterhub status."""

    available: bool = False


@strawberry.type
class AwsVpc:
    """GraphQL type for the AWS VPC."""

    vpc_id: str
    name: Optional[str] = None
    cidr_block: str
    is_default: bool


@strawberry.type
class AwsVpcs:
    """GraphQL type for the AWS VPCs."""

    vpcs: list[AwsVpc]


@strawberry.type
class AwsSubnet:
    """GraphQL type for the AWS subnet."""

    subnet_id: str
    name: Optional[str] = None
    cidr_block: str
    av_zone: str


@strawberry.type
class AwsSubnets:
    """GraphQL type for the AWS subnets."""

    subnets: list[AwsSubnet]


@strawberry.input
class ClusterQueueActionsInput:
    """GraphQL type for the cluster queue actions input."""

    cluster_name: str
    queue_id: int
    action: ClusterQueueAction = ClusterQueueAction.cancel


@strawberry.type
class RemoveQueueActionSuccess:
    """GraphQL type for the success response of removing a queue action."""

    message: str = "Queue action removed successfully"
