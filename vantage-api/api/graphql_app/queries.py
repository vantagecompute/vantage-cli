"""Core module for the GraphQL queries."""
from typing import Union

import strawberry

from api.graphql_app.helpers import (
    ClusterQueryAuthorization,
    NotebookQueryAuthorization,
    QueryQueueActionAuthorization,
    SshKeyQueryAuthorization,
    StorageQueryAuthorization,
    SubnetQueryAuthorization,
    VpcQueryAuthorization,
)
from api.graphql_app.resolvers import cluster, notebooks, partition, storage
from api.graphql_app.types import (
    AwsNodesFilters,
    AwsNodeTypes,
    AwsRegionsDescribed,
    AwsSshKeys,
    AwsSubnets,
    AwsVpcs,
    CloudAccountNotFound,
    Cluster,
    ClusterAvailableForDeletion,
    ClusterNode,
    ClusterNotFound,
    ClusterPartition,
    ClusterQueue,
    ClusterQueueActions,
    Connection,
    InvalidInput,
    JupyterHubStatus,
    MountPointCheck,
    NotebookServer,
    NotebookServerNotFound,
    NotebookServerProgress,
    ParameterValidationError,
    Partition,
    SlurmClusterConfig,
    Storage,
    UnexpectedBehavior,
)


@strawberry.type
class Query:

    """Query class."""

    clusters: Connection[Cluster] = strawberry.field(
        resolver=cluster.get_clusters, permission_classes=[ClusterQueryAuthorization]
    )

    slurm_config: Connection[SlurmClusterConfig] = strawberry.field(
        resolver=cluster.get_slurm_config, permission_classes=[ClusterQueryAuthorization]
    )

    slurm_partitions: Connection[ClusterPartition] = strawberry.field(
        resolver=cluster.get_slurm_partitions, permission_classes=[ClusterQueryAuthorization]
    )

    slurm_nodes: Connection[ClusterNode] = strawberry.field(
        resolver=cluster.get_slurm_nodes, permission_classes=[ClusterQueryAuthorization]
    )

    slurm_queue: Connection[ClusterQueue] = strawberry.field(
        resolver=cluster.get_slurm_queue, permission_classes=[ClusterQueryAuthorization]
    )

    cluster_queue_actions: Connection[ClusterQueueActions] = strawberry.field(
        resolver=cluster.get_cluster_queue_actions, permission_classes=[QueryQueueActionAuthorization]
    )

    check_cluster_availability_for_deletion: Union[
        ClusterAvailableForDeletion, ClusterNotFound
    ] = strawberry.field(
        resolver=cluster.cluster_available_for_deletion, permission_classes=[ClusterQueryAuthorization]
    )

    storages: Connection[Storage] = strawberry.field(
        resolver=storage.get_storage, permission_classes=[StorageQueryAuthorization]
    )

    ssh_keys: Union[AwsSshKeys, ParameterValidationError, InvalidInput] = strawberry.field(
        resolver=cluster.get_ssh_key_pairs, permission_classes=[SshKeyQueryAuthorization]
    )

    vpcs: Union[AwsVpcs, ParameterValidationError, InvalidInput] = strawberry.field(
        resolver=cluster.get_vpcs, permission_classes=[VpcQueryAuthorization]
    )

    subnets: Union[AwsSubnets, ParameterValidationError, InvalidInput] = strawberry.field(
        resolver=cluster.get_subnets, permission_classes=[SubnetQueryAuthorization]
    )

    check_mount_point: Union[
        MountPointCheck, InvalidInput, UnexpectedBehavior, ClusterNotFound
    ] = strawberry.field(resolver=storage.check_mount_point, permission_classes=[StorageQueryAuthorization])

    aws_node_picker: Connection[AwsNodeTypes] = strawberry.field(
        resolver=cluster.aws_node_picker, permission_classes=[ClusterQueryAuthorization]
    )

    aws_node_picker_filter_values: Connection[AwsNodesFilters] = strawberry.field(
        resolver=cluster.aws_node_picker_filter_values, permission_classes=[ClusterQueryAuthorization]
    )

    enabled_aws_regions: Union[AwsRegionsDescribed, CloudAccountNotFound] = strawberry.field(
        resolver=cluster.enabled_aws_regions, permission_classes=[ClusterQueryAuthorization]
    )

    partitions: Connection[Partition] = strawberry.field(
        resolver=partition.get_cluster_partitions, permission_classes=[ClusterQueryAuthorization]
    )

    notebook_servers: Connection[NotebookServer] = strawberry.field(
        resolver=notebooks.get_notebook_server, permission_classes=[NotebookQueryAuthorization]
    )

    notebook_server_progress: Union[
        NotebookServerNotFound,
        NotebookServerProgress,
    ] = strawberry.field(resolver=notebooks.check_progress, permission_classes=[NotebookQueryAuthorization])

    jupyterhub_status: JupyterHubStatus = strawberry.field(
        resolver=notebooks.get_jupyterhub_status, permission_classes=[NotebookQueryAuthorization]
    )
