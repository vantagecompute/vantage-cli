"""Core module for the GraphQL mutations."""
from typing import Union

import strawberry

from api.graphql_app import resolvers
from api.graphql_app.helpers import (
    AddQueueActionMutationAuthorization,
    CreateClusterMutationAuthorization,
    CreateNotebookMutationAuthorization,
    CreateStorageMutationAuthorization,
    DeleteClusterMutationAuthorization,
    DeleteNotebookMutationAuthorization,
    DeleteStorageMutationAuthorization,
    HasClusterResourceRequests,
    HasStorageResourceRequests,
    MountStorageMutationAuthorization,
    RemoveQueueActionMutationAuthorization,
    UnmountStorageMutationAuthorization,
    UpdateClusterMutationAuthorization,
    UpdateStorageMutationAuthorization,
    UploadSlurmInfoAuthorization,
)
from api.graphql_app.types import (
    Cluster,
    ClusterCouldNotBeDeployed,
    ClusterDeleted,
    ClusterNameInUse,
    ClusterNotFound,
    ClusterQueueActions,
    ClusterQueueActionsInput,
    CreateClusterInput,
    CreateNotebookInput,
    CreatePartitionInput,
    CreateStorageInput,
    DuplicatedMountPoint,
    DuplicatedStorageId,
    DuplicatedStorageName,
    FileSystemMisconfigured,
    Info,
    InvalidInput,
    InvalidProviderInput,
    JSONScalar,
    MissingAwsPermissions,
    MountPoint,
    MountStorageInput,
    NotebookServer,
    NotebookServerAlreadyExists,
    NotebookServerDeleted,
    NotebookServerNotFound,
    Partition,
    PartitionDeleted,
    PartitionNotFound,
    RemoveQueueActionSuccess,
    Storage,
    StorageDeleted,
    StorageNotFound,
    StorageUnmounting,
    UnexpectedBehavior,
    UnmountStorageInput,
    UpdateClusterRecordInput,
    UpdatePartitionInput,
    UploadSlurmConfigSuccess,
    UploadSlurmNodesSuccess,
    UploadSlurmPartitionsSuccess,
    UploadSlurmQueueSuccess,
)


@strawberry.type
class Mutation:

    """Mutation class."""

    @strawberry.mutation(permission_classes=[CreateClusterMutationAuthorization, HasClusterResourceRequests])
    async def create_cluster(
        self,
        info: Info,
        create_cluster_input: CreateClusterInput,
    ) -> ClusterNameInUse | InvalidInput | Cluster | ClusterCouldNotBeDeployed | UnexpectedBehavior:
        """Create a cluster mutation."""
        return await resolvers.cluster.create_cluster(info, create_cluster_input)

    @strawberry.mutation(permission_classes=[CreateClusterMutationAuthorization])
    async def create_demo_cluster(
        self,
        info: Info,
    ) -> (
        ClusterNameInUse
        | InvalidProviderInput
        | InvalidInput
        | Cluster
        | ClusterCouldNotBeDeployed
        | UnexpectedBehavior
    ):
        """Create a demo cluster mutation."""
        return await resolvers.cluster.create_demo_cluster(info)

    @strawberry.mutation(permission_classes=[UpdateClusterMutationAuthorization])
    async def update_cluster(
        self, info: Info, update_cluster_input: UpdateClusterRecordInput
    ) -> Union[Cluster, ClusterNotFound]:
        """Update a cluster mutation."""
        return await resolvers.cluster.update_cluster(info, update_cluster_input)

    @strawberry.mutation(permission_classes=[DeleteClusterMutationAuthorization])
    async def delete_cluster(
        self, info: Info, cluster_name: str
    ) -> Union[ClusterNotFound, InvalidProviderInput, ClusterDeleted, UnexpectedBehavior]:
        """Delete a cluster mutation."""
        return await resolvers.cluster.delete_cluster(info, cluster_name)

    @strawberry.mutation(permission_classes=[UploadSlurmInfoAuthorization])
    async def upload_slurm_config(
        self, info: Info, client_id: str, config: JSONScalar
    ) -> Union[ClusterNotFound, UploadSlurmConfigSuccess]:
        """Upload a cluster's Slurm configuration."""
        return await resolvers.cluster.upload_slurm_config(info, client_id, config)

    @strawberry.mutation(permission_classes=[UploadSlurmInfoAuthorization])
    async def upload_slurm_partitions(
        self, info: Info, client_id: str, partitions: JSONScalar
    ) -> Union[ClusterNotFound, UploadSlurmPartitionsSuccess]:
        """Upload a cluster's Slurm partitions."""
        return await resolvers.cluster.upload_slurm_partitions(info, client_id, partitions)

    @strawberry.mutation(permission_classes=[UploadSlurmInfoAuthorization])
    async def upload_slurm_queue(
        self, info: Info, client_id: str, queue: JSONScalar
    ) -> Union[ClusterNotFound, UploadSlurmQueueSuccess]:
        """Upload a cluster's Slurm queue."""
        return await resolvers.cluster.upload_slurm_queue(info, client_id, queue)

    @strawberry.mutation(permission_classes=[UploadSlurmInfoAuthorization])
    async def upload_slurm_nodes(
        self, info: Info, client_id: str, nodes: JSONScalar
    ) -> Union[ClusterNotFound, UploadSlurmNodesSuccess]:
        """Upload a cluster's Slurm nodes."""
        return await resolvers.cluster.upload_slurm_nodes(info, client_id, nodes)

    @strawberry.mutation(permission_classes=[UploadSlurmInfoAuthorization])
    async def report_agent_health(self, info: Info, client_id: str, interval: int) -> None:
        """Report Vantage Agent health."""
        return await resolvers.cluster.report_agent_health(info, client_id, interval)

    @strawberry.mutation(permission_classes=[CreateStorageMutationAuthorization, HasStorageResourceRequests])
    async def create_storage(
        self,
        info: Info,
        create_storage_input: CreateStorageInput,
    ) -> Union[
        DuplicatedStorageId,
        Storage,
        UnexpectedBehavior,
        DuplicatedStorageName,
        MissingAwsPermissions,
        FileSystemMisconfigured,
        InvalidInput,
    ]:
        """Create a Storage mutation."""
        return await resolvers.storage.create_storage(info, create_storage_input)

    @strawberry.mutation(permission_classes=[UpdateStorageMutationAuthorization])
    async def update_storage(
        self, info: Info, id: int, name: str
    ) -> Union[DuplicatedStorageName, Storage, StorageNotFound]:
        """Update a Storage mutation."""
        return await resolvers.storage.update_storage(info, id, name)

    @strawberry.mutation(permission_classes=[DeleteStorageMutationAuthorization])
    async def delete_storage(
        self, info: Info, storage_id: int
    ) -> Union[StorageNotFound, StorageDeleted, UnexpectedBehavior]:
        """Delete a storage mutation."""
        return await resolvers.storage.delete_storage(info, storage_id)

    @strawberry.mutation(permission_classes=[MountStorageMutationAuthorization])
    async def mount_storage(
        self,
        info: Info,
        mount_storage_input: MountStorageInput,
    ) -> Union[
        StorageNotFound, UnexpectedBehavior, InvalidInput, MountPoint, DuplicatedMountPoint, ClusterNotFound
    ]:
        """Mount a Storage into a cluster."""
        return await resolvers.storage.mount_storage(info, mount_storage_input)

    @strawberry.mutation(permission_classes=[UnmountStorageMutationAuthorization])
    async def unmount_storage(
        self,
        info: Info,
        unmount_storage_input: UnmountStorageInput,
    ) -> Union[StorageNotFound, UnexpectedBehavior, InvalidInput, StorageUnmounting]:
        """Unmount a Storage from cluster."""
        return await resolvers.storage.unmount_storage(info, unmount_storage_input)

    @strawberry.mutation(permission_classes=[UpdateClusterMutationAuthorization])
    async def create_partition(
        self, info: Info, create_partition_input: CreatePartitionInput
    ) -> Union[InvalidInput, Partition]:
        """Add a new partition to an existing cluster."""
        return await resolvers.create_partition(info=info, create_partition_input=create_partition_input)

    @strawberry.mutation(permission_classes=[UpdateClusterMutationAuthorization])
    async def update_partition(
        self, info: Info, update_partition_input: UpdatePartitionInput
    ) -> Union[InvalidInput, Partition]:
        """Update a partition of an existing cluster."""
        return await resolvers.update_partition(info=info, update_partition_input=update_partition_input)

    @strawberry.mutation(permission_classes=[DeleteClusterMutationAuthorization])
    async def delete_partition(
        self, info: Info, cluster_name: str, partition_name: str
    ) -> Union[InvalidInput, PartitionDeleted]:
        """Delete a partition from an existing cluster."""
        return await resolvers.delete_partition(
            info=info, cluster_name=cluster_name, partition_name=partition_name
        )

    @strawberry.mutation(permission_classes=[CreateNotebookMutationAuthorization])
    async def create_jupyter_server(
        self, info: Info, create_notebook_input: CreateNotebookInput
    ) -> Union[ClusterNotFound, NotebookServerAlreadyExists, PartitionNotFound, NotebookServer]:
        """Create a jupyter server."""
        return await resolvers.create_notebook(info=info, create_notebook_input=create_notebook_input)

    @strawberry.mutation(permission_classes=[DeleteNotebookMutationAuthorization])
    async def delete_jupyter_server(
        self, info: Info, notebook_server_name: str
    ) -> Union[NotebookServerNotFound, NotebookServerDeleted]:
        """Delete a jupyter server."""
        return await resolvers.delete_notebook_server(info=info, notebook_server_name=notebook_server_name)

    @strawberry.mutation(permission_classes=[AddQueueActionMutationAuthorization])
    async def add_queue_action(
        self, info: Info, input: ClusterQueueActionsInput
    ) -> Union[InvalidInput, ClusterQueueActions]:
        """Add a queue action to the cluster queue actions table."""
        return await resolvers.cluster.add_queue_action(
            info=info, cluster_name=input.cluster_name, queue_id=input.queue_id, action=input.action
        )

    @strawberry.mutation(permission_classes=[RemoveQueueActionMutationAuthorization])
    async def remove_queue_action(self, info: Info, id: int) -> Union[InvalidInput, RemoveQueueActionSuccess]:
        """Remove a queue action from the cluster queue actions table."""
        return await resolvers.cluster.remove_queue_action(info=info, id=id)
