"""Core module for defining GraphQL resolvers."""
import asyncio
import random
import re
import secrets
import threading
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Union

import strawberry
from botocore.exceptions import ClientError, ParamValidationError
from fastapi import status
from httpx import HTTPStatusError
from loguru import logger
from sqlalchemy import delete, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.sql.expression import Delete, Insert, Select, Update

from api.cfn_app import cfn_ops
from api.constants import CLUSTER_ALL_POSSIBLE_NAMES
from api.ec2_app import ec2_ops
from api.graphql_app.helpers import (
    build_connection,
    clean_cluster_name,
    cluster_name_to_client_id,
    delete_dns_record,
    get_partitions_and_node_info,
    get_role_arn_of_cloud_account,
    is_valid_instance_for_region,
    monitor_aws_cluster_status,
    set_up_cluster_config_on_keycloak,
    threaded_break_out_slurm_information,
    upsert_slurm_information,
)
from api.graphql_app.resolvers.storage import _unmount_storage_async
from api.graphql_app.types import (
    AwsNodesFilters,
    AwsNodesOrderingInput,
    AwsNodeTypes,
    AwsRegionsDescribed,
    AwsSshKeys,
    AwsSubnet,
    AwsSubnets,
    AwsVpc,
    AwsVpcs,
    CloudAccountNotFound,
    Cluster,
    ClusterAvailableForDeletion,
    ClusterAvailableForDeletionReason,
    ClusterCouldNotBeDeployed,
    ClusterDeleted,
    ClusterNameInUse,
    ClusterNode,
    ClusterNotFound,
    ClusterOrderingInput,
    ClusterPartition,
    ClusterProviderEnum,
    ClusterQueue,
    ClusterQueueAction,
    ClusterQueueActions,
    ClusterRegion,
    Connection,
    CreateClusterInput,
    Info,
    InvalidInput,
    InvalidProviderInput,
    JSONScalar,
    ParameterValidationError,
    RemoveQueueActionSuccess,
    SlurmClusterConfig,
    UnexpectedBehavior,
    UpdateClusterRecordInput,
    UploadSlurmConfigSuccess,
    UploadSlurmNodesSuccess,
    UploadSlurmPartitionsSuccess,
    UploadSlurmQueueSuccess,
)
from api.identity.management_api import backend_client
from api.schemas.aws import AwsOpsConfig
from api.sql_app import enums, models
from api.sql_app.session import create_async_session


async def cluster_available_for_deletion(
    info: Info, cluster_name: str
) -> ClusterAvailableForDeletion | ClusterNotFound:
    """Check if a cluster is available for deletion.

    By design, on premises cluster will always be available for deletion.
    """
    organization_id = info.context.token_data.organization

    async with info.context.db_session(organization_id) as sess:
        query = select(models.ClusterModel).where(models.ClusterModel.name == cluster_name)
        cluster: models.ClusterModel | None = (await sess.execute(query)).scalar_one_or_none()

        if cluster is None:
            return ClusterNotFound()

        if cluster.provider == ClusterProviderEnum.on_prem:
            return ClusterAvailableForDeletion(is_available=True)
        else:
            query = select(models.MountPointModel).where(models.MountPointModel.cluster_name == cluster_name)
            storage: models.StorageModel | None = (await sess.execute(query)).scalar_one_or_none()
            if storage is not None:
                return ClusterAvailableForDeletion(
                    is_available=False, reason=ClusterAvailableForDeletionReason.cluster_has_mount_points
                )

            role_arn = await get_role_arn_of_cloud_account(int(cluster.cloud_account_id), sess)
            assert role_arn is not None  # mypy assert

            region: str | None = cluster.creation_parameters.get("region_name")
            assert region is not None  # mypy assert

            credentials: AwsOpsConfig = {"role_arn": role_arn, "region_name": region}

            stack_status = cfn_ops.get_stack_status(
                stack_name=clean_cluster_name(str(cluster.name)),
                cfn_config=credentials,
            )
            if stack_status is None:
                return ClusterAvailableForDeletion(is_available=True)
            if stack_status not in [
                "CREATE_COMPLETE",
                "CREATE_FAILED",
                "CREATE_IN_PROGRESS",
                "ROLLBACK_COMPLETE",
                "UPDATE_COMPLETE",
                "UPDATE_ROLLBACK_COMPLETE",
                "DELETE_COMPLETE",
            ]:
                return ClusterAvailableForDeletion(
                    is_available=False,
                    reason=ClusterAvailableForDeletionReason.unknown_error,
                )

            stack_resources = cfn_ops.get_stack_resources(
                stack_name=str(cluster.name),
                cfn_config=credentials,
            )
            if stack_resources is None:
                return ClusterAvailableForDeletion(is_available=True)

            vpc_info = next(
                (item for item in stack_resources if item["ResourceType"] == "AWS::EC2::VPC"),
                None,
            )
            assert vpc_info is not None  # mypy assert
            vpc_id = vpc_info["PhysicalResourceId"]

            ec2_instances_in_vpc = ec2_ops.list_instances_by_vpc_id(
                vpc_id=vpc_id, role_arn=role_arn, region_name=region
            )
            if len(ec2_instances_in_vpc) > 1:
                return ClusterAvailableForDeletion(
                    is_available=False, reason=ClusterAvailableForDeletionReason.cluster_has_compute_nodes
                )

    return ClusterAvailableForDeletion(is_available=True)


async def get_ssh_key_pairs(
    info: Info, cloud_account_id: int, region: ClusterRegion
) -> AwsSshKeys | ParameterValidationError | InvalidInput:
    """Get SSH key pairs for a specified cloud account and region.

    Args:
    ----
        info (Info): The resolver info containing context and other metadata.
        cloud_account_id (int): The ID of the cloud account to retrieve SSH key pairs from.
        region (ClusterRegion): The region to retrieve SSH key pairs from.

    Returns:
    -------
        Union[AwsSshKeys, ParameterValidationError, InvalidInput]:
            - AwsSshKeys: If the SSH key pairs are successfully retrieved.
            - ParameterValidationError: If there is a parameter validation error.
            - InvalidInput: If the cloud account is not found or access is denied.

    """
    organization_id = info.context.token_data.organization

    async with info.context.db_session(organization_id) as sess:
        role_arn = await get_role_arn_of_cloud_account(cloud_account_id, sess)
        if role_arn is None:
            return InvalidInput(message="Cloud account not found")

    try:
        key_pairs = ec2_ops.get_ssh_key_pairs(role_arn=role_arn, region_name=region.value)
        return AwsSshKeys(key_pair_names=(key_pair.get("KeyName") for key_pair in key_pairs))
    except ParamValidationError as err:
        logger.exception(err)
        return ParameterValidationError(message=str(err))
    except ClientError as err:
        if err.response["Error"]["Code"] in ["UnauthorizedOperation", "AccessDenied"]:
            return InvalidInput(message=str(err))


async def get_vpcs(
    info: Info, cloud_account_id: int, region: ClusterRegion
) -> AwsVpcs | ParameterValidationError | InvalidInput:
    """Get all VPCs for a specified cloud account and region."""
    organization_id = info.context.token_data.organization
    async with info.context.db_session(organization_id) as sess:
        role_arn = await get_role_arn_of_cloud_account(cloud_account_id, sess)
        if role_arn is None:
            return InvalidInput(message="Cloud account not found")

    try:
        vpcs = ec2_ops.get_vpcs(role_arn=role_arn, region_name=region.value)
        vpc_outputs = []
        for vpc in vpcs:
            for tag in vpc.get("Tags", []):
                if tag.get("Key") == "Name":
                    name = tag.get("Value")
                    break
            else:
                name = None
            vpc_outputs.append(
                AwsVpc(
                    vpc_id=vpc.get("VpcId"),
                    name=name,
                    cidr_block=vpc.get("CidrBlock"),
                    is_default=vpc.get("IsDefault"),
                )
            )
        return AwsVpcs(vpcs=vpc_outputs)
    except ParamValidationError as err:
        logger.exception(err)
        return ParameterValidationError(message=str(err))
    except ClientError as err:
        if err.response["Error"]["Code"] in ["UnauthorizedOperation", "AccessDenied"]:
            return InvalidInput(message=str(err))
        raise err


async def get_subnets(
    info: Info, cloud_account_id: int, region: ClusterRegion, vpc_id: str
) -> AwsSubnets | ParameterValidationError | InvalidInput:
    """Get all subnets for a specified cloud account and region."""
    organization_id = info.context.token_data.organization
    async with info.context.db_session(organization_id) as sess:
        role_arn = await get_role_arn_of_cloud_account(cloud_account_id, sess)
        if role_arn is None:
            return InvalidInput(message="Cloud account not found")

    try:
        subnets = ec2_ops.get_subnets(role_arn=role_arn, region_name=region.value, vpc_id=vpc_id)
        subnet_outputs = []
        for subnet in subnets:
            for tag in subnet.get("Tags", []):
                if tag.get("Key") == "Name":
                    name = tag.get("Value")
                    break
            else:
                name = None
            subnet_outputs.append(
                AwsSubnet(
                    subnet_id=subnet.get("SubnetId"),
                    name=name,
                    cidr_block=subnet.get("CidrBlock"),
                    av_zone=subnet.get("AvailabilityZone"),
                )
            )
        return AwsSubnets(subnets=subnet_outputs)
    except ParamValidationError as err:
        logger.exception(err)
        return ParameterValidationError(message=str(err))
    except ClientError as err:
        if err.response["Error"]["Code"] in ["UnauthorizedOperation", "AccessDenied"]:
            return InvalidInput(message=str(err))
        raise err


async def get_clusters(
    info: Info,
    first: int = 10,
    after: int = 1,
    filters: Optional[JSONScalar] = None,
    subfilters: Optional[JSONScalar] = None,
    ordering: Optional[ClusterOrderingInput] = None,
) -> Connection[Cluster]:
    """Get all clusters."""
    clusters = await build_connection(
        info=info,
        first=first,
        model=models.ClusterModel,
        scalar_type=Cluster,
        after=after,
        filters=filters,
        subfilters=subfilters,
        ordering=ordering,
        model_relations=[
            models.ClusterModel.cloud_account,
            models.ClusterModel.mount_points,
            models.ClusterModel.slurm_cluster_config,
            models.ClusterModel.nodes,
            models.ClusterModel.partitions,
            models.ClusterModel.cluster_partitions,
            models.ClusterModel.queue,
            models.ClusterModel.cluster_queue_actions,
        ],
    )

    async with info.context.db_session(info.context.token_data.organization) as sess:
        for index in range(len(clusters.edges)):
            partitions: list[models.PartitionModel] = await get_partitions_and_node_info(
                clusters.edges[index].node.cluster_partitions, sess
            )
            clusters.edges[index].node.cluster_partitions = partitions
    return clusters


async def create_demo_cluster(
    info: Info,
) -> Union[
    ClusterNameInUse,
    InvalidProviderInput,
    InvalidInput,
    Cluster,
    ClusterCouldNotBeDeployed,
    UnexpectedBehavior,
]:
    """Create a demo cluster resolver.

    This endpoint primarily handles variable preparation for the
    CreateClusterInput type and invokes the create_cluster resolver.

    The approach involves pre-generating a list of all available
    names at the start of the app and subsequently comparing them
    against the database to determine availability.

    If no available names are found, the resolver returns the ClusterNameInUse
    type, indicating that the user has exceeded their quota for demo clusters.
    In such cases, expanding the pool of available names is recommended.
    """
    organization_id = info.context.token_data.organization

    async with info.context.db_session(organization_id) as sess:
        query = select(models.ClusterModel.name).where(
            models.ClusterModel.name.in_(CLUSTER_ALL_POSSIBLE_NAMES)
        )
        records = (await sess.execute(query)).scalars().all()

    available_names = CLUSTER_ALL_POSSIBLE_NAMES - set(records)
    if not available_names:
        return ClusterNameInUse()
    name = random.choice(list(available_names))

    create_cluster_response = await create_cluster(
        info=info,
        create_cluster_input=CreateClusterInput(
            name=name,
            provider=ClusterProviderEnum.on_prem,
            description=(
                "This cluster was created as a local demonstration cluster. It should "
                "be used for trying out Vantage features or testing things out."
            ),
        ),
    )

    return create_cluster_response


async def create_cluster(  # noqa: C901
    info: Info, create_cluster_input: CreateClusterInput
) -> Union[
    ClusterNameInUse,
    InvalidInput,
    Cluster,
    ClusterCouldNotBeDeployed,
    UnexpectedBehavior,
]:
    """Create a cluster resolver."""
    cluster_name_regex = r"^(?=.{1,128}$)[a-zA-Z0-9-]*[a-zA-Z0-9]$"
    if not re.match(cluster_name_regex, create_cluster_input.name):
        return InvalidInput(
            message="Cluster name must contain only alphanumeric characters and hyphens with no spaces"
        )

    if (
        create_cluster_input.provider_attributes is None or create_cluster_input.partitions is None
    ) and create_cluster_input.provider == ClusterProviderEnum.aws.value:
        return InvalidInput(
            message="Either provider_attributes and partitions shall be informed for aws cluster type."
        )
    if create_cluster_input.provider == ClusterProviderEnum.aws.value:
        partitions_names = [partition.name for partition in create_cluster_input.partitions]
        if len(partitions_names) != len(set(partitions_names)):
            return InvalidInput(
                message=(
                    "Multiple partitions with the same name are not allowed."
                    "Please review your configuration and ensure that each partition has a unique name."
                )
            )

        if create_cluster_input.provider_attributes is None:
            return InvalidInput(message="Provider attributes are required for AWS clusters")

        compute_node_types = [partition.node_type for partition in create_cluster_input.partitions]
        aws_attributes = create_cluster_input.provider_attributes.aws
        if not await is_valid_instance_for_region(
            info, aws_attributes.head_node_instance_type, aws_attributes.region_name
        ):
            return InvalidInput(
                message=(
                    f"Head node instance type {aws_attributes.head_node_instance_type} for region"
                    f" {aws_attributes.region_name} is not valid"
                )
            )
        elif any(
            [
                not await is_valid_instance_for_region(info, node_type, aws_attributes.region_name)
                for node_type in compute_node_types
            ]
        ):
            return InvalidInput(
                message=(
                    f"Some of compute node instance type {compute_node_types} for region"
                    f" {aws_attributes.region_name} is not valid"
                )
            )

    organization_id = info.context.token_data.organization

    client_id = cluster_name_to_client_id(create_cluster_input.name, organization_id)
    slurm_cluster_name = clean_cluster_name(create_cluster_input.name)

    query: Select | Insert
    async with info.context.db_session(organization_id) as sess:
        role_arn = (
            await get_role_arn_of_cloud_account(
                create_cluster_input.provider_attributes.aws.cloud_account_id, sess
            )
            if create_cluster_input.provider_attributes is not None
            else None
        )

        query = select(models.ClusterModel).where(models.ClusterModel.name == create_cluster_input.name)
        record = (await sess.execute(query)).scalar()
        if record is not None:
            return ClusterNameInUse()

        client_secret = create_cluster_input.secret or secrets.token_urlsafe(32)
        jupyterhub_token = secrets.token_urlsafe(32)
        creation_parameters = (
            strawberry.asdict(create_cluster_input.provider_attributes.aws)
            if create_cluster_input.provider_attributes is not None
            else {}
        )
        creation_parameters = {**creation_parameters, "jupyterhub_token": jupyterhub_token}

        payload = {
            "name": create_cluster_input.name,
            "client_id": client_id,
            "provider": create_cluster_input.provider,
            "status": enums.ClusterStatusEnum.preparing.value
            if create_cluster_input.provider == ClusterProviderEnum.aws.value
            else enums.ClusterStatusEnum.ready.value,
            "description": create_cluster_input.description,
            "owner_email": info.context.token_data.email,
            "creation_parameters": creation_parameters,
            "cloud_account_id": create_cluster_input.provider_attributes.aws.cloud_account_id
            if create_cluster_input.provider_attributes is not None and role_arn is not None
            else None,
        }
        query = insert(models.ClusterModel).values(**payload).returning(models.ClusterModel)
        cluster = (await sess.execute(query)).one()

        ## Insert the partitions
        if create_cluster_input.provider == ClusterProviderEnum.aws.value:
            payload = [
                {
                    "name": partition.name,
                    "node_type": partition.node_type,
                    "max_node_count": partition.max_node_count,
                    "cluster_name": create_cluster_input.name,
                    "is_default": partition.is_default,
                }
                for partition in create_cluster_input.partitions
            ]
            query = insert(models.ClusterPartitionsModel).values(payload)
            await sess.execute(query)

        client_uuid = str(uuid.uuid4())
        try:
            await set_up_cluster_config_on_keycloak(
                client_uuid=client_uuid,
                client_id=client_id,
                client_name=client_id,
                client_description=(
                    f"Client for authentication purposes of cluster {create_cluster_input.name}"
                    f" - Org ID: {organization_id}"
                ),
                client_secret=client_secret,
                organization_id=organization_id,
            )
        except HTTPStatusError:
            return UnexpectedBehavior(message="Unexpected behavior")

        if create_cluster_input.provider == ClusterProviderEnum.aws.value:
            aws_attributes = create_cluster_input.provider_attributes.aws
            aws_attributes.head_node_instance_type = aws_attributes.head_node_instance_type
            aws_attributes.region_name = aws_attributes.region_name.value
            partitions = create_cluster_input.partitions

            if role_arn is None:
                logger.warning("Cloud account not found. Deleting the Keycloak client...")
                await backend_client.delete(f"/admin/realms/vantage/clients/{client_uuid}")
                return InvalidInput(message="Cloud account not found")
            cfn_config = AwsOpsConfig(
                region_name=aws_attributes.region_name,
                role_arn=role_arn,
            )

            try:
                cfn_ops.apply_template(
                    config=cfn_config,
                    slurm_cluster_name=slurm_cluster_name,
                    api_cluster_name=create_cluster_input.name,
                    client_id=client_id,
                    client_secret=client_secret,
                    jupyterhub_token=jupyterhub_token,
                    partitions=[strawberry.asdict(partition) for partition in partitions],
                    **strawberry.asdict(aws_attributes),
                )
            except Exception as e:
                logger.exception(f"Error happened when creating a cloud cluster: {e}")
                await backend_client.delete(f"/admin/realms/vantage/clients/{client_uuid}")
                return ClusterCouldNotBeDeployed()

            monitor_aws_cluster_status(
                organization_id,
                aws_attributes.region_name,
                role_arn,
                slurm_cluster_name,
                create_cluster_input.name,
            )

        await sess.commit()

    return Cluster(**cluster)


async def update_cluster(
    info: Info, update_cluster_input: UpdateClusterRecordInput
) -> Union[Cluster, ClusterNotFound]:
    """Update a cluster resolver."""
    async with info.context.db_session(info.context.token_data.organization) as sess:
        query = (
            update(models.ClusterModel)
            .where(models.ClusterModel.name == update_cluster_input.name)
            .values(**strawberry.asdict(update_cluster_input))
            .returning(models.ClusterModel)
        )
        cluster = (await sess.execute(query)).one_or_none()

        if cluster is None:
            return ClusterNotFound()

        await sess.commit()

    return Cluster(**cluster)


def _delete_cluster(
    info: Info,
    cluster_name: str,
    client_id: str,
    instance_id: str,
    vpc_id: str,
    cfn_config: AwsOpsConfig,
):
    asyncio.run(_delete_aws_cluster_async(info, cluster_name, client_id, instance_id, vpc_id, cfn_config))


async def _delete_aws_cluster_async(
    info: Info,
    cluster_name: str,
    client_id: str,
    instance_id: str,
    vpc_id: str,
    cfn_config: AwsOpsConfig,
):
    query: Select | Delete

    session = await create_async_session(info.context.token_data.organization, False)
    async with session() as sess:
        query = select(models.MountPointModel).where(models.MountPointModel.cluster_name == cluster_name)
        mount_points: List[models.MountPointModel] = (await sess.execute(query)).scalars().all()
        await sess.close()

    for mount_point in mount_points:
        await _unmount_storage_async(
            db=info.context.token_data.organization,
            aws_config=cfn_config,
            path=str(mount_point.mount_point),
            instance_id=instance_id,
            storage_id=str(mount_point.storage_id),
            vpc_id=vpc_id,
            mount_point_id=int(mount_point.id),
        )

    slurm_cluster_name = clean_cluster_name(cluster_name)
    cfn_ops.destroy_stack(slurm_cluster_name, cfn_config=cfn_config)

    delete_dns_record(client_id=client_id)

    session = await create_async_session(info.context.token_data.organization, False)
    async with session() as sess:
        query = delete(models.ClusterModel).where(models.ClusterModel.name == cluster_name)
        await sess.execute(query)
        await sess.commit()
        await sess.close()


async def delete_cluster(
    info: Info, cluster_name: str
) -> Union[ClusterNotFound, InvalidProviderInput, ClusterDeleted, UnexpectedBehavior]:
    """Delete a cluster resolver."""
    query: Select | Delete | Update

    client_id = cluster_name_to_client_id(cluster_name, info.context.token_data.organization)

    async with info.context.db_session(info.context.token_data.organization) as sess:
        query = select(models.ClusterModel).where(models.ClusterModel.name == cluster_name)
        cluster = (await sess.execute(query)).scalar_one_or_none()

        if cluster is None:
            return ClusterNotFound()

        logger.debug(f"Deleting cluster {cluster_name} whose provider is {cluster.provider}")

        if cluster.provider == ClusterProviderEnum.aws.value:
            cloud_account_role_arn = await get_role_arn_of_cloud_account(cluster.cloud_account_id, sess)
            assert isinstance(cluster.creation_parameters, dict)
            region_name = cluster.creation_parameters.get("region_name")
            assert isinstance(region_name, str)
            assert cloud_account_role_arn is not None
            cfn_config = AwsOpsConfig(region_name=region_name, role_arn=cloud_account_role_arn)

            payload = {"status": "deleting"}
            query = (
                update(models.ClusterModel)
                .where(models.ClusterModel.name == cluster_name)
                .values(**payload)
                .returning(models.ClusterModel)
            )
        else:
            query = delete(models.ClusterModel).where(models.ClusterModel.name == cluster_name)

        await sess.execute(query)

        # fetch the client data
        client_response = await backend_client.get(
            "/admin/realms/vantage/clients", params={"clientId": client_id}
        )
        if len(client_response.json()) != 1:
            return UnexpectedBehavior(
                message=(
                    "Unexpected behaviour in which the cluster record"
                    " exists but the client doesn't. Contact support"
                )
            )
        client = client_response.json()[0]

        # fetch the client's service account user data
        service_account_user_response = await backend_client.get(
            f"/admin/realms/vantage/clients/{client.get('id')}/service-account-user"
        )
        service_account_user_response.raise_for_status()

        client_response = await backend_client.delete(f"/admin/realms/vantage/clients/{client.get('id')}")
        if client_response.status_code != status.HTTP_204_NO_CONTENT:
            logger.error(
                f"Couldn't delete client whose uuid={client.get('id')} and id={client.get('clientId')}"
            )
            return UnexpectedBehavior(message="Couldn't delete client, contact support for details")

        await sess.commit()

    if cluster.provider == ClusterProviderEnum.aws.value:
        stack_resources = cfn_ops.get_stack_resources(
            stack_name=clean_cluster_name(cluster_name), cfn_config=cfn_config
        )

        if stack_resources is None:
            query = delete(models.ClusterModel).where(models.ClusterModel.name == cluster_name)
            await sess.execute(query)
            await sess.commit()
        else:
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

            thread = threading.Thread(
                target=_delete_cluster,
                args=(info, cluster_name, client_id, instance_id, vpc_id, cfn_config),
            )

            thread.start()

    return ClusterDeleted()


async def upload_slurm_config(
    info: Info, client_id: str, config: dict[str, str]
) -> Union[UploadSlurmConfigSuccess, ClusterNotFound]:
    """Upload slurm config resolver."""
    session = await create_async_session(info.context.token_data.organization, False)
    async with session() as sess:
        try:
            await upsert_slurm_information(config, client_id, models.SlurmClusterConfig, sess)
        except NoResultFound:
            logger.error(
                (
                    f"Attempt to upsert slurm config for client_id {client_id} "
                    "failed because no cluster was found with that client_id"
                )
            )
            return ClusterNotFound()
    return UploadSlurmConfigSuccess()


async def upload_slurm_partitions(
    info: Info, client_id: str, partitions: dict[str, dict[str, str]]
) -> Union[UploadSlurmPartitionsSuccess, ClusterNotFound]:
    """Upload slurm partitions resolver."""
    session = await create_async_session(info.context.token_data.organization, False)
    async with session() as sess:
        try:
            await upsert_slurm_information(partitions, client_id, models.AllPartitionInfo, sess)
        except NoResultFound:
            logger.error(
                (
                    f"Attempt to upsert slurm partitions for client_id {client_id} "
                    "failed because no cluster was found with that client_id"
                )
            )
            return ClusterNotFound()
    thread = threading.Thread(
        target=threaded_break_out_slurm_information,
        args=(
            models.AllPartitionInfo,
            models.PartitionModel,
            info.context.token_data.organization,
            client_id,
        ),
    )
    thread.start()
    return UploadSlurmPartitionsSuccess()


async def upload_slurm_nodes(
    info: Info, client_id: str, nodes: dict[str, dict[str, str]]
) -> Union[UploadSlurmNodesSuccess, ClusterNotFound]:
    """Upload slurm nodes resolver."""
    session = await create_async_session(info.context.token_data.organization, False)
    async with session() as sess:
        try:
            await upsert_slurm_information(nodes, client_id, models.AllNodeInfo, sess)
        except NoResultFound:
            logger.error(
                (
                    f"Attempt to upsert slurm nodes for client_id {client_id} "
                    "failed because no cluster was found with that client_id"
                )
            )
            return ClusterNotFound()

    thread = threading.Thread(
        target=threaded_break_out_slurm_information,
        args=(models.AllNodeInfo, models.NodeModel, info.context.token_data.organization, client_id),
    )
    thread.start()
    return UploadSlurmNodesSuccess()


async def get_slurm_config(
    info: Info,
    first: int = 10,
    after: int = 1,
    filters: Optional[JSONScalar] = None,
    subfilters: Optional[JSONScalar] = None,
    ordering: Optional[ClusterOrderingInput] = None,
) -> Connection[SlurmClusterConfig]:
    """Get the slurm configurations registered in the database."""
    return await build_connection(
        info=info,
        first=first,
        model=models.SlurmClusterConfig,
        scalar_type=SlurmClusterConfig,
        after=after,
        filters=filters,
        subfilters=subfilters,
        ordering=ordering,
        model_relations=[models.SlurmClusterConfig.cluster],
    )


async def enabled_aws_regions(
    info: Info, cloud_account_id: int
) -> Union[CloudAccountNotFound, AwsRegionsDescribed]:
    """Return a list of available regions for a given cloud account."""
    organization_id = info.context.token_data.organization
    async with info.context.db_session(organization_id) as sess:
        role_arn = await get_role_arn_of_cloud_account(cloud_account_id, sess)
        if role_arn is None:
            return CloudAccountNotFound()

    enabled_regions = ec2_ops.list_enabled_regions(role_arn)
    return AwsRegionsDescribed(
        enabled_regions=[ClusterRegion(region) for region in enabled_regions],
        disabled_regions=[
            ClusterRegion(region) for region in ClusterRegion if region.value not in enabled_regions
        ],
    )


async def aws_node_picker(
    info: Info,
    first: int = 10,
    after: int = 1,
    filters: Optional[JSONScalar] = None,
    subfilters: Optional[JSONScalar] = None,
    ordering: Optional[AwsNodesOrderingInput] = None,
) -> Connection[AwsNodeTypes]:
    """Get all available AWS node types."""
    return await build_connection(
        info=info,
        first=first,
        model=models.AwsNodeTypesModel,
        scalar_type=AwsNodeTypes,
        after=after,
        filters=filters,
        subfilters=subfilters,
        ordering=ordering,
        model_relations=[],
    )


async def get_slurm_partitions(
    info: Info,
    first: int = 10,
    after: int = 1,
    filters: Optional[JSONScalar] = None,
    subfilters: Optional[JSONScalar] = None,
    ordering: Optional[ClusterOrderingInput] = None,
) -> Connection[ClusterPartition]:
    """Get slurm partitions registered in the database."""
    return await build_connection(
        info=info,
        first=first,
        model=models.PartitionModel,
        scalar_type=ClusterPartition,
        after=after,
        filters=filters,
        subfilters=subfilters,
        ordering=ordering,
        model_relations=[models.PartitionModel.cluster],
    )


async def get_slurm_queue(
    info: Info,
    first: int = 10,
    after: int = 1,
    filters: Optional[JSONScalar] = None,
    subfilters: Optional[JSONScalar] = None,
    ordering: Optional[ClusterOrderingInput] = None,
) -> Connection[ClusterQueue]:
    """Get slurm queue registered in the database."""
    return await build_connection(
        info=info,
        first=first,
        model=models.QueueModel,
        scalar_type=ClusterQueue,
        after=after,
        filters=filters,
        subfilters=subfilters,
        ordering=ordering,
        model_relations=[models.QueueModel.cluster, models.QueueModel.cluster_queue_actions],
    )


async def get_slurm_nodes(
    info: Info,
    first: int = 10,
    after: int = 1,
    filters: Optional[JSONScalar] = None,
    subfilters: Optional[JSONScalar] = None,
    ordering: Optional[ClusterOrderingInput] = None,
) -> Connection[ClusterNode]:
    """Get slurm nodes registered in the database."""
    return await build_connection(
        info=info,
        first=first,
        model=models.NodeModel,
        scalar_type=ClusterNode,
        after=after,
        filters=filters,
        subfilters=subfilters,
        ordering=ordering,
        model_relations=[models.NodeModel.cluster],
    )


async def get_cluster_queue_actions(
    info: Info,
    first: int = 10,
    after: int = 1,
    filters: Optional[JSONScalar] = None,
    subfilters: Optional[JSONScalar] = None,
    ordering: Optional[ClusterOrderingInput] = None,
) -> Connection[ClusterQueueActions]:
    """Get cluster queue actions registered in the database."""
    return await build_connection(
        info=info,
        first=first,
        model=models.ClusterQueueActionsModel,
        scalar_type=ClusterQueueActions,
        after=after,
        filters=filters,
        subfilters=subfilters,
        ordering=ordering,
        model_relations=[models.ClusterQueueActionsModel.queue, models.ClusterQueueActionsModel.cluster],
    )


async def report_agent_health(info: Info, client_id: str, interval: int) -> None:
    """Record the last update from the Vantage Agent."""
    session = await create_async_session(info.context.token_data.organization, True)
    async with session() as sess:
        cluster_name_subquery = (
            select(models.ClusterModel.name)
            .where(models.ClusterModel.client_id == client_id)
            .scalar_subquery()
        )
        query = (
            pg_insert(models.AgentHealthCheckModel)
            .values(cluster_name=cluster_name_subquery, interval=interval)
            .on_conflict_do_update(
                index_elements=[models.AgentHealthCheckModel.cluster_name],
                set_={
                    models.AgentHealthCheckModel.interval: interval,
                    models.AgentHealthCheckModel.last_reported: datetime.now(timezone.utc),
                },
            )
        )
        try:
            await sess.execute(query)
            await sess.commit()
        except IntegrityError:
            logger.info(
                (
                    f"Attempt to record agent health for {client_id=} "
                    "failed because no cluster was found with that client_id"
                )
            )


async def aws_node_picker_filter_values(
    info: Info,
    first: int = 10,
    after: int = 1,
    filters: Optional[JSONScalar] = None,
    subfilters: Optional[JSONScalar] = None,
) -> Connection[AwsNodeTypes]:
    """Get all filters available for querying the AWS Node Types."""
    return await build_connection(
        info=info,
        first=first,
        model=models.AwsNodeTypesFiltersModel,
        scalar_type=AwsNodesFilters,
        after=after,
        filters=filters,
        subfilters=subfilters,
        ordering=None,
        model_relations=[],
    )


async def upload_slurm_queue(
    info: Info, client_id: str, queue: dict[str, dict[str, str]]
) -> Union[UploadSlurmQueueSuccess, ClusterNotFound]:
    """Upload slurm queue resolver."""
    logger.debug(f"Uploading slurm queue for client_id {client_id} with data: {queue}")
    session = await create_async_session(info.context.token_data.organization, False)
    async with session() as sess:
        try:
            await upsert_slurm_information(queue, client_id, models.AllQueueInfo, sess)
        except NoResultFound:
            logger.error(
                (
                    f"Attempt to upsert slurm queue for client_id {client_id} "
                    "failed because no cluster was found with that client_id"
                )
            )
            return ClusterNotFound()
    logger.debug(f"Starting thread to break out slurm queue information for client_id {client_id}")
    thread = threading.Thread(
        target=threaded_break_out_slurm_information,
        args=(
            models.AllQueueInfo,
            models.QueueModel,
            info.context.token_data.organization,
            client_id,
        ),
    )
    thread.start()
    return UploadSlurmQueueSuccess()


async def add_queue_action(
    info: Info, cluster_name: str, queue_id: int, action: ClusterQueueAction
) -> Union[InvalidInput, ClusterQueueActions]:
    """Add a queue action to the cluster queue actions table."""
    organization_id = info.context.token_data.organization

    async with info.context.db_session(organization_id) as sess:
        # Check if queue exists
        queue_query = select(models.QueueModel).where(models.QueueModel.id == queue_id)
        queue = (await sess.execute(queue_query)).scalar_one_or_none()

        if queue is None:
            return InvalidInput(message="Queue not found")

        # Check if action already exists for this cluster and queue
        existing_query = select(models.ClusterQueueActionsModel).where(
            models.ClusterQueueActionsModel.cluster_name == cluster_name,
            models.ClusterQueueActionsModel.queue_id == queue_id,
        )
        existing_action = (await sess.execute(existing_query)).scalar_one_or_none()

        if existing_action is not None:
            return InvalidInput(message="Action already exists for this cluster and queue")

        # Insert new action
        insert_query = (
            insert(models.ClusterQueueActionsModel)
            .values(cluster_name=cluster_name, queue_id=queue_id, action=action)
            .returning(models.ClusterQueueActionsModel)
        )
        result = await sess.execute(insert_query)
        await sess.commit()
        return ClusterQueueActions(**result.one())


async def remove_queue_action(info: Info, id: int) -> Union[InvalidInput, RemoveQueueActionSuccess]:
    """Remove a queue action from the cluster queue actions table."""
    organization_id = info.context.token_data.organization

    async with info.context.db_session(organization_id) as sess:
        # Check if action exists
        query = select(models.ClusterQueueActionsModel).where(models.ClusterQueueActionsModel.id == id)
        action = (await sess.execute(query)).scalar_one_or_none()

        if action is None:
            return InvalidInput(message="Queue action not found")

        # Delete the action
        delete_query = delete(models.ClusterQueueActionsModel).where(models.ClusterQueueActionsModel.id == id)
        await sess.execute(delete_query)
        await sess.commit()

    return RemoveQueueActionSuccess()
