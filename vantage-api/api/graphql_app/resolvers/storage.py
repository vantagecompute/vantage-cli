"""Storage resolvers."""
import asyncio
import threading
from enum import Enum
from typing import Dict, Optional, Union

from botocore.exceptions import ClientError
from loguru import logger
from sqlalchemy import and_, delete, insert, join, or_, select, update
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.orm import joinedload, subqueryload
from sqlalchemy.sql.expression import Delete, Insert, Select, Update

from api.cfn_app import cfn_ops
from api.efs_app import efs_ops
from api.graphql_app.helpers import build_connection, clean_cluster_name
from api.graphql_app.types import (
    CheckMountPointInput,
    CloudAccount,
    Cluster,
    ClusterNotFound,
    Connection,
    CreateStorageInput,
    DuplicatedMountPoint,
    DuplicatedStorageId,
    DuplicatedStorageName,
    FileSystemMisconfigured,
    Info,
    InvalidInput,
    JSONScalar,
    MissingAwsPermissions,
    MountPoint,
    MountPointCheck,
    MountStorageInput,
    Storage,
    StorageDeleted,
    StorageNotFound,
    StorageOrderingInput,
    StorageSourceEnum,
    StorageUnmounted,
    StorageUnmounting,
    UnexpectedBehavior,
    UnmountStorageInput,
)
from api.schemas.aws import AwsOpsConfig
from api.sql_app import models
from api.sql_app.schemas import CloudAccountRow, StorageRow
from api.sql_app.session import create_async_session


async def get_storage(
    info: Info,
    first: int = 10,
    after: int = 1,
    filters: Optional[JSONScalar] = None,
    subfilters: Optional[JSONScalar] = None,
    ordering: Optional[StorageOrderingInput] = None,
) -> Connection[Storage]:
    """Get all storages."""
    return await build_connection(
        info=info,
        first=first,
        model=models.StorageModel,
        scalar_type=Storage,
        after=after,
        filters=filters,
        subfilters=subfilters,
        ordering=ordering,
        model_relations=[models.StorageModel.mount_points, models.StorageModel.cloud_account],
    )


async def create_storage(  # noqa: C901
    info: Info, create_storage_input: CreateStorageInput
) -> Union[
    DuplicatedStorageId,
    Storage,
    UnexpectedBehavior,
    DuplicatedStorageName,
    MissingAwsPermissions,
    FileSystemMisconfigured,
    InvalidInput,
]:
    """Create a storage resolver."""
    organization = info.context.token_data.organization

    query: Union[Select, Insert]

    async with info.context.db_session(organization) as sess:
        query = select(models.StorageModel).where(
            or_(
                models.StorageModel.name == create_storage_input.name,
                models.StorageModel.fs_id == create_storage_input.fs_id,
            )
        )
        record = (await sess.execute(query)).scalar()
        if record is not None:
            if record.name == create_storage_input.name:
                return DuplicatedStorageName()
            else:
                return DuplicatedStorageId()

        fs_id = create_storage_input.fs_id
        try:
            cloud_account_query = select(models.CloudAccountModel).where(
                models.CloudAccountModel.id == create_storage_input.cloud_account_id
            )
            cloud_account_row = (await sess.execute(cloud_account_query)).scalar_one_or_none()
            if cloud_account_row is None:
                return InvalidInput(message="Cloud account not found with ID provided.")

            cloud_account = CloudAccountRow.from_orm(cloud_account_row)

            if create_storage_input.source.value == StorageSourceEnum.vantage:
                new_storage_id = efs_ops.create_efs(
                    fs_name=create_storage_input.name,
                    region_name=create_storage_input.region.value,
                    role_arn=cloud_account.attributes["role_arn"],
                )

                if new_storage_id is None:
                    return UnexpectedBehavior(
                        message="Was not possible to create the efs. The Efs name conflicts or it's invalid"
                    )
                fs_id = new_storage_id
            else:
                if fs_id is None:
                    return InvalidInput(message="The fs_id is required for non-vantage sources")
                imported_storage = efs_ops.check_efs(
                    fs_id=fs_id,
                    region_name=create_storage_input.region.value,
                    role_arn=cloud_account.attributes["role_arn"],
                )
                if imported_storage is False:
                    return FileSystemMisconfigured(
                        message="The file system is not tagged with the correct tags or it was not found."
                    )
        except ClientError as err:
            if err.response["Error"]["Code"] == "UnauthorizedOperation":
                return MissingAwsPermissions(message=str(err))
            elif err.response["Error"]["Code"] == "AccessDenied":
                return MissingAwsPermissions(message=str(err))
            else:
                return UnexpectedBehavior(message=str(err))

        payload = {
            "fs_id": fs_id,
            "name": create_storage_input.name,
            "region": create_storage_input.region.value,
            "source": create_storage_input.source.value,
            "owner": info.context.token_data.email,
            "cloud_account_id": cloud_account.id,
        }

        query = insert(models.StorageModel).values(**payload)
        await sess.execute(query)
        await sess.commit()

    async with info.context.db_session(organization) as sess:
        query = (
            select(models.StorageModel)
            .select_from(
                join(
                    models.StorageModel,
                    models.CloudAccountModel,
                    models.StorageModel.cloud_account_id == models.CloudAccountModel.id,
                )
            )
            .where(models.StorageModel.name == create_storage_input.name)
        )
        storage = (await sess.execute(query)).scalar_one()

    StorageRow.update_forward_refs()
    return Storage(**StorageRow.from_orm(storage).dict())


async def update_storage(
    info: Info, id: int, name: str
) -> Union[DuplicatedStorageName, Storage, StorageNotFound]:
    """Update a Storage resolver."""
    query: Select | Update
    organization = info.context.token_data.organization
    async with info.context.db_session(organization) as sess:
        query = (
            update(models.StorageModel)
            .where(
                models.StorageModel.id == id,
                models.StorageModel.owner == info.context.token_data.email,
            )
            .values({"name": name})
            .returning(models.StorageModel)
        )
        try:
            updated_storage_row = (await sess.execute(query)).one_or_none()
        except IntegrityError as err:
            logger.exception(err)
            return DuplicatedStorageName(message=f"Storage name {name} is already in use")
        else:
            if updated_storage_row is None:
                return StorageNotFound()
            await sess.commit()

    async with info.context.db_session(organization) as sess:
        query = (
            select(models.StorageModel)
            .where(models.StorageModel.id == id)
            .options(
                joinedload(models.StorageModel.cloud_account), joinedload(models.StorageModel.mount_points)
            )
        )
        storage_row = (await sess.execute(query)).unique().scalar_one()

    StorageRow.update_forward_refs()
    storage_row_dict = StorageRow.from_orm(storage_row).dict()
    return Storage(
        cloud_account=CloudAccount(**storage_row_dict.pop("cloud_account")),
        mount_points=[MountPoint(**mp.dict()) for mp in storage_row_dict.pop("mount_points")],
        **storage_row_dict,
    )


async def delete_storage(
    info: Info, storage_id: int
) -> Union[StorageNotFound, StorageDeleted, UnexpectedBehavior]:
    """Delete a storage resolver."""
    query: Union[Select, Delete]

    async with info.context.db_session(info.context.token_data.organization) as sess:
        query = (
            select(models.StorageModel)
            .select_from(
                join(
                    models.StorageModel,
                    models.CloudAccountModel,
                    models.StorageModel.cloud_account_id == models.CloudAccountModel.id,
                )
            )
            .where(
                models.StorageModel.id == storage_id,
                models.StorageModel.owner == info.context.token_data.email,
            )
        )
        try:
            storage_row = (await sess.execute(query)).scalars().one()
        except NoResultFound:
            return StorageNotFound(
                message=(
                    f"Either there's no storage with ID {storage_id}" " or it belongs to a different owner"
                )
            )
        else:
            assert storage_row is not None  # mypy assert
            StorageRow.update_forward_refs()
            storage = StorageRow.from_orm(storage_row)
            assert storage.cloud_account is not None  # mypy assert

        if storage.source == StorageSourceEnum.vantage:
            efs_ops.delete_efs(
                fs_id=storage.fs_id,
                region_name=storage.region,
                role_arn=storage.cloud_account.attributes["role_arn"],
            )

        query = delete(models.StorageModel).where(models.StorageModel.id == storage_id)

        await sess.execute(query)

        await sess.commit()

    return StorageDeleted()


def _mount_task(
    db: str,
    credentials: Dict[str, Union[str, Enum]],
    path: str,
    instance_id: str,
    storage_id: str,
    public_subnet_id: str,
    private_subnet_id: str,
    vpc_id: str,
    mount_point_id: int,
):
    asyncio.run(
        _mount_storage_async(
            db=db,
            credentials=credentials,
            path=path,
            instance_id=instance_id,
            storage_id=storage_id,
            public_subnet_id=public_subnet_id,
            private_subnet_id=private_subnet_id,
            vpc_id=vpc_id,
            mount_point_id=mount_point_id,
        )
    )


async def _mount_storage_async(
    db: str,
    credentials: Dict[str, Union[str, Enum]],
    path: str,
    instance_id: str,
    storage_id: str,
    public_subnet_id: str,
    private_subnet_id: str,
    vpc_id: str,
    mount_point_id: int,
):
    session = await create_async_session(db, False)
    async with session() as sess:
        async with sess.begin():
            try:
                is_available = await efs_ops.mount_storage(
                    credentials=credentials,
                    path=path,
                    instance_id=instance_id,
                    storage_id=storage_id,
                    public_subnet_id=public_subnet_id,
                    private_subnet_id=private_subnet_id,
                    vpc_id=vpc_id,
                )

                payload = {"status": "mounted", "error": None}
                if not is_available:
                    payload = {
                        "status": "error",
                        "error": "Error while mounting storage. Contact the support",
                    }

                query = (
                    update(models.MountPointModel)
                    .where(
                        models.MountPointModel.id == mount_point_id,
                    )
                    .values(**payload)
                    .returning(models.MountPointModel)
                )

                await sess.execute(query)
                await sess.commit()
                await sess.close()

                return True

            except Exception as e:
                logger.error(f"Error during the mount storage execution {str(e)}")
                payload = {"status": "error", "error": str(e)}
                query = (
                    update(models.MountPointModel)
                    .where(
                        models.MountPointModel.id == mount_point_id,
                    )
                    .values(**payload)
                    .returning(models.MountPointModel)
                )
                await sess.execute(query)
                await sess.commit()
                await sess.close()
                return UnexpectedBehavior(message="Was not possible to mount the storage")


def _unmount_task(
    db: str,
    aws_config: AwsOpsConfig,
    path: str,
    instance_id: str,
    storage_id: str,
    vpc_id: str,
    mount_point_id: int,
):
    asyncio.run(
        _unmount_storage_async(
            db=db,
            aws_config=aws_config,
            path=path,
            instance_id=instance_id,
            storage_id=storage_id,
            vpc_id=vpc_id,
            mount_point_id=mount_point_id,
        )
    )


async def _unmount_storage_async(
    db: str,
    aws_config: AwsOpsConfig,
    path: str,
    instance_id: str,
    storage_id: str,
    vpc_id: str,
    mount_point_id: int,
):
    """Unmount a storage resolver."""
    response: UnexpectedBehavior | StorageUnmounted
    query: Delete | Update

    session = await create_async_session(db, False)
    async with session() as sess:
        async with sess.begin():
            try:
                deleted = efs_ops.umount_storage(
                    path=path,
                    instance_id=instance_id,
                    fs_id=storage_id,
                    vpc_id=vpc_id,
                    aws_config=aws_config,
                )

                response = StorageUnmounted()
                if not deleted:
                    payload = {
                        "status": "error",
                        "error": "Was not possible to detach the storage. Check if mount point if busy and try again.",  # noqa
                    }
                    query = (
                        update(models.MountPointModel)
                        .where(
                            models.MountPointModel.id == mount_point_id,
                        )
                        .values(**payload)
                        .returning(models.MountPointModel)
                    )
                    response = UnexpectedBehavior(
                        message="Was not possible to umount the storage. Check if mount point if busy and try again."  # noqa
                    )
                else:
                    query = delete(models.MountPointModel).where(models.MountPointModel.id == mount_point_id)

                await sess.execute(query)
                await sess.commit()
                await sess.close()

                return response

            except Exception as e:
                logger.error(f"Error during the unmount storage execution {str(e)}")
                payload = {"status": "error", "error": str(e)}
                query = (
                    update(models.MountPointModel)
                    .where(
                        models.MountPointModel.id == mount_point_id,
                    )
                    .values(**payload)
                    .returning(models.MountPointModel)
                )
                await sess.execute(query)
                await sess.commit()
                await sess.close()
                return UnexpectedBehavior(message="Was not possible to unmount the storage")


async def mount_storage(
    info: Info, mount_storage_input: MountStorageInput
) -> Union[
    StorageNotFound, UnexpectedBehavior, ClusterNotFound, MountPoint, InvalidInput, DuplicatedMountPoint
]:
    """Mount a storage resolver."""
    organization = info.context.token_data.organization
    async with info.context.db_session(organization) as sess:
        cluster_query = select(models.ClusterModel).where(
            models.ClusterModel.name == mount_storage_input.cluster_name
        )
        try:
            cluster: models.ClusterModel = (await sess.execute(cluster_query)).scalars().one()
        except NoResultFound:
            return ClusterNotFound()

        storage_and_cloud_account_query = (
            select(
                models.StorageModel.id.label("storage_id"),
                models.CloudAccountModel.attributes.label("cloud_account_attributes"),
            )
            .select_from(
                join(
                    models.StorageModel,
                    models.CloudAccountModel,
                    models.StorageModel.cloud_account_id == models.CloudAccountModel.id,
                )
            )
            .where(models.StorageModel.fs_id == mount_storage_input.fs_id)
        )
        storage_and_cloud_account_row = (await sess.execute(storage_and_cloud_account_query)).first()
        if storage_and_cloud_account_row is None:
            return StorageNotFound()

        storage_id, cloud_account_attributes = storage_and_cloud_account_row

        existing_mount_point_query = (
            select(models.MountPointModel)
            .join(models.ClusterModel)
            .join(models.StorageModel)
            .where(
                and_(
                    models.ClusterModel.name == mount_storage_input.cluster_name,
                    models.MountPointModel.mount_point == mount_storage_input.path,
                    models.StorageModel.fs_id == mount_storage_input.fs_id,
                )
            )
        )
        existing_mount_point = (await sess.execute(existing_mount_point_query)).scalar_one_or_none()
        if existing_mount_point is not None:
            return DuplicatedMountPoint()

        credentials: AwsOpsConfig = {
            "role_arn": cloud_account_attributes["role_arn"],
            "region_name": mount_storage_input.region.value,
        }

        stack_resources = cfn_ops.get_stack_resources(
            stack_name=clean_cluster_name(cluster.name),
            cfn_config=credentials,
        )
        if stack_resources is None:
            return UnexpectedBehavior(message="Impossible to get the stack resources")

        head_node_info = next(
            (item for item in stack_resources if item["LogicalResourceId"] == "HeadNodeInstance"), None
        )

        public_subnet_info = next(
            (
                item
                for item in stack_resources
                if item["ResourceType"] == "AWS::EC2::Subnet"
                and item["LogicalResourceId"].startswith("PublicSubnet")
            ),
            None,
        )
        private_subnet_info = next(
            (
                item
                for item in stack_resources
                if item["ResourceType"] == "AWS::EC2::Subnet"
                and item["LogicalResourceId"].startswith("PrivateSubnet")
            ),
            None,
        )
        vpc_info = next(
            (item for item in stack_resources if item["ResourceType"] == "AWS::EC2::VPC"),
            None,
        )

        if not (head_node_info and public_subnet_info and private_subnet_info and vpc_info):
            return UnexpectedBehavior(
                message="Impossible to find the cluster resources to attach the storage"
            )

        instance_id = head_node_info["PhysicalResourceId"]
        public_subnet_id = public_subnet_info["PhysicalResourceId"]
        private_subnet_id = private_subnet_info["PhysicalResourceId"]
        vpc_id = vpc_info["PhysicalResourceId"]

        is_valid = efs_ops.check_mount_point_path(
            aws_config=credentials, path=mount_storage_input.path, instance_id=instance_id
        )

        if not is_valid:
            return InvalidInput(message="Either path to mount is not valid or it's in use by the cluster")

        payload = {
            "cluster_name": cluster.name,
            "client_id": cluster.client_id,
            "mount_point": mount_storage_input.path,
            "storage_id": int(storage_id),
            "status": "mounting",
        }

        query = insert(models.MountPointModel).values(**payload).returning(models.MountPointModel.id)
        mount_point_id = (await sess.execute(query)).scalar_one()
        await sess.commit()

    async with info.context.db_session(organization) as sess:
        mount_point_query = (
            select(models.MountPointModel)
            .where(models.MountPointModel.id == mount_point_id)
            .options(subqueryload(models.MountPointModel.storage))
            .options(subqueryload(models.MountPointModel.cluster))
        )
        mount_point = (await sess.execute(mount_point_query)).scalar_one()

        thread = threading.Thread(
            target=_mount_task,
            args=(
                info.context.token_data.organization,
                credentials,
                mount_storage_input.path,
                instance_id,
                mount_storage_input.fs_id,
                public_subnet_id,
                private_subnet_id,
                vpc_id,
                mount_point.id,
            ),
        )
        thread.start()

        await sess.refresh(mount_point)
        await sess.refresh(mount_point.storage)
        await sess.refresh(mount_point.cluster)

        # hack to avoid max recursion error.
        # fixed in Pydantic v2
        return MountPoint(
            id=mount_point.id,
            cluster_name=mount_point.cluster.name,
            storage_id=mount_point.storage.id,
            client_id=mount_point.client_id,
            mount_point=mount_point.mount_point,
            created_at=mount_point.created_at,
            status=mount_point.status,
            error=mount_point.error,
            storage=Storage(
                id=mount_point.storage.id,
                fs_id=mount_point.storage.fs_id,
                name=mount_point.storage.name,
                region=mount_point.storage.region,
                cloud_account_id=mount_point.storage.cloud_account_id,
                source=StorageSourceEnum(mount_point.storage.source),
                owner=mount_point.storage.owner,
                created_at=mount_point.storage.created_at,
                cloud_account=CloudAccount(
                    id=mount_point.storage.cloud_account.id,
                    provider=mount_point.storage.cloud_account.provider,
                    name=mount_point.storage.cloud_account.name,
                    assisted_cloud_account=mount_point.storage.cloud_account.assisted_cloud_account,
                    description=mount_point.storage.cloud_account.description,
                    attributes=mount_point.storage.cloud_account.attributes,
                    created_at=mount_point.storage.cloud_account.created_at,
                    updated_at=mount_point.storage.cloud_account.updated_at,
                ),
                mount_points=[],
            ),
            cluster=Cluster(
                name=mount_point.cluster.name,
                description=mount_point.cluster.description,
                status=mount_point.cluster.status,
                client_id=mount_point.cluster.client_id,
                owner_email=mount_point.cluster.owner_email,
                provider=mount_point.cluster.provider,
                cloud_account_id=mount_point.cluster.cloud_account_id,
                creation_parameters=mount_point.cluster.creation_parameters,
            ),
        )


async def unmount_storage(
    info: Info, unmount_storage_input: UnmountStorageInput
) -> Union[StorageNotFound, InvalidInput, UnexpectedBehavior, StorageUnmounting]:
    """Unmount a storage resolver."""
    async with info.context.db_session(info.context.token_data.organization) as sess:
        mount_point_query = (
            select(
                models.MountPointModel.id.label("mount_point_id"),
                models.StorageModel.id.label("storage_id"),
                models.StorageModel.fs_id.label("fs_id"),
                models.StorageModel.region.label("region"),
                models.MountPointModel.mount_point.label("path"),
                models.ClusterModel.client_id.label("client_id"),
                models.ClusterModel.name.label("cluster_name"),
                models.CloudAccountModel.attributes.label("cloud_account_attributes"),
            )
            .join(models.StorageModel, models.MountPointModel.storage_id == models.StorageModel.id)
            .join(models.ClusterModel, models.MountPointModel.cluster_name == models.ClusterModel.name)
            .join(
                models.CloudAccountModel, models.StorageModel.cloud_account_id == models.CloudAccountModel.id
            )
            .where(
                and_(
                    models.MountPointModel.storage_id == unmount_storage_input.storage_id,
                    models.MountPointModel.cluster_name == unmount_storage_input.cluster_name,
                )
            )
        )

        try:
            mount_point = (await sess.execute(mount_point_query)).first()
            if mount_point is None:
                return StorageNotFound(
                    message=(
                        f"Either there's no mount point with Storage Id {unmount_storage_input.storage_id}"
                        " or it belongs to a different owner"
                    )
                )
        except NoResultFound:
            return StorageNotFound(
                message=(
                    f"Either there's no mount point with Storage Id {unmount_storage_input.storage_id}"
                    " or it belongs to a different owner"
                )
            )
        (
            mount_point_id,
            storage_id,
            fs_id,
            region,
            path,
            cluster_id,
            cluster_name,
            cloud_account_attributes,
        ) = mount_point
        logger.debug(
            f"Retrieved mount point details: {mount_point_id=}, {storage_id=}, {fs_id=}, {region=}, "
            f"{path=}, {cluster_name=}, {cluster_id=}"
        )

        assert isinstance(cloud_account_attributes, dict)  # mypy assert
        assert isinstance(cloud_account_attributes.get("role_arn"), str)  # mypy assert

        credentials: AwsOpsConfig = {"role_arn": cloud_account_attributes["role_arn"], "region_name": region}

        stack_resources = cfn_ops.get_stack_resources(
            stack_name=clean_cluster_name(cluster_name),
            cfn_config=credentials,
        )
        if stack_resources is None:
            return UnexpectedBehavior(message="Impossible to get the stack resources")

        head_node_info = next(
            (item for item in stack_resources if item["LogicalResourceId"] == "HeadNodeInstance"), None
        )
        vpc_info = next(
            (item for item in stack_resources if item["ResourceType"] == "AWS::EC2::VPC"),
            None,
        )
        if not head_node_info or not vpc_info:
            return UnexpectedBehavior(
                message="Impossible to find the cluster resources to umount the storage"
            )

        instance_id = head_node_info["PhysicalResourceId"]
        vpc_id = vpc_info["PhysicalResourceId"]

        payload = {"status": "deleting", "error": None}

        query = (
            update(models.MountPointModel)
            .where(
                models.MountPointModel.id == mount_point_id,
            )
            .values(**payload)
            .returning(models.MountPointModel)
        )
        await sess.execute(query)
        await sess.commit()
        await sess.close()

    thread = threading.Thread(
        target=_unmount_task,
        args=(
            info.context.token_data.organization,
            credentials,
            path,
            instance_id,
            fs_id,
            vpc_id,
            mount_point_id,
        ),
    )
    thread.start()

    return StorageUnmounting()


async def check_mount_point(
    info: Info, check_mount_point: CheckMountPointInput
) -> Union[MountPointCheck, InvalidInput, UnexpectedBehavior, ClusterNotFound]:
    """Check if the mount point is available."""
    async with info.context.db_session(info.context.token_data.organization) as sess:
        cluster_query = select(models.ClusterModel).where(
            models.ClusterModel.name == check_mount_point.cluster_name
        )
        try:
            cluster: models.ClusterModel = (await sess.execute(cluster_query)).scalars().one()
        except NoResultFound:
            return ClusterNotFound()

        mount_point_query = select(models.MountPointModel).where(
            and_(
                models.MountPointModel.cluster_name == check_mount_point.cluster_name,
                models.MountPointModel.mount_point == check_mount_point.path,
            )
        )
        try:
            mount_point = (await sess.execute(mount_point_query)).scalars().one_or_none()
            if mount_point is not None:
                return MountPointCheck(is_available=False)
        except Exception as e:
            logger.exception(f"Fail to verify the mount point path in database {str(e)}")
            return UnexpectedBehavior(message="Fail to verify the mount point path.")

        cloud_account_attributes_query = select(models.CloudAccountModel.attributes).where(
            models.CloudAccountModel.id == check_mount_point.cloud_account_id
        )
        cloud_account_attributes = (await sess.execute(cloud_account_attributes_query)).scalar_one_or_none()
        if cloud_account_attributes is None:
            return InvalidInput(message="Cloud account not found with ID provided.")

        credentials: AwsOpsConfig = {
            "role_arn": cloud_account_attributes["role_arn"],
            "region_name": check_mount_point.region.value,
        }

        stack_resources = cfn_ops.get_stack_resources(
            stack_name=clean_cluster_name(cluster.name),
            cfn_config=credentials,
        )
        if stack_resources is None:
            return UnexpectedBehavior(message="Impossible to get the stack resources")

        head_node_info = next(
            (item for item in stack_resources if item["LogicalResourceId"] == "HeadNodeInstance"), None
        )

        if head_node_info is None:
            return UnexpectedBehavior(
                message="Impossible to find the cluster resources to check the mount point"
            )

        instance_id = head_node_info["PhysicalResourceId"]

        is_valid = efs_ops.check_mount_point_path(
            aws_config=credentials, path=check_mount_point.path, instance_id=instance_id
        )

        return MountPointCheck(is_available=is_valid)
