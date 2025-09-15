"""Core module for AWS EFS related operations."""
import time
from collections.abc import AsyncGenerator
from enum import Enum
from typing import Dict, Literal, Union

import boto3
from loguru import logger
from mypy_boto3_efs.client import EFSClient
from mypy_boto3_efs.paginator import DescribeMountTargetsPaginator
from mypy_boto3_efs.type_defs import FileSystemDescriptionResponseTypeDef
from mypy_boto3_ssm.client import SSMClient

from api.ec2_app.ec2_ops import get_ec2_client, tag_instance, untag_instance
from api.schemas.aws import AwsOpsConfig
from api.settings import SETTINGS
from api.sts_app.sts_ops import AssumedSessionCredentials, get_session_credentials


def _get_efs_client(credentials: AssumedSessionCredentials) -> EFSClient:
    return boto3.client("efs", **credentials, endpoint_url=SETTINGS.AWS_ENDPOINT_URL)


def _get_ssm_client(credentials: AssumedSessionCredentials | dict | None = None) -> SSMClient:
    """Receive AWS credentials and return the SSM boto3 client."""
    if credentials is None:
        credentials = {}
    client: SSMClient = boto3.client("ssm", **credentials, endpoint_url=SETTINGS.AWS_ENDPOINT_URL)
    return client


def _wait_mount_target(efs: EFSClient, fs_id: str, mount_target_id: str, timeout: int = 120):
    """Wait for the mount target to be ready."""
    response = efs.describe_mount_targets(MountTargetId=mount_target_id)
    status = response["MountTargets"][0]["LifeCycleState"]
    passed_time = timeout

    while status not in ["available", "deleted", "error"]:
        if passed_time < 0:
            status = "error"
        try:
            response = efs.describe_mount_targets(MountTargetId=mount_target_id)
            status = response["MountTargets"][0]["LifeCycleState"]
            logger.debug(f"Waiting mount target {mount_target_id}.")
        except efs.exceptions.MountTargetNotFound:
            status = "deleted"
            break
        except Exception as e:
            logger.exception(
                f"Error while waiting for mounting target: mount_target_id={mount_target_id} fs_id={fs_id} exception={e}"  # noqa
            )
            raise e
        passed_time -= 2
        time.sleep(2)
    logger.debug("mount target ready.")
    return status


def create_efs(fs_name: str, role_arn: str, region_name: str) -> Union[str, None]:
    """Create an EFS."""
    logger.debug(
        "Creating EFS: {params}".format(
            params={"fs_name": fs_name, "role_arn": role_arn, "region_name": region_name}
        )
    )

    credentials, _ = get_session_credentials(role_arn, region_name)
    client: EFSClient = _get_efs_client(credentials)

    tags = [{"Key": "ManagedBy", "Value": "Vantage"}, {"Key": "Name", "Value": f"{fs_name}"}]

    fs_exist = client.describe_file_systems(CreationToken=fs_name)

    if len(fs_exist.get("FileSystems")) > 0:
        return

    storage: FileSystemDescriptionResponseTypeDef = client.create_file_system(
        ThroughputMode="elastic", PerformanceMode="generalPurpose", Tags=tags, CreationToken=fs_name
    )

    return storage["FileSystemId"]


def check_efs(fs_id: str, role_arn: str, region_name: str) -> Literal[True, False]:
    """Check if the given EFS is valid."""
    logger.debug("Checking if EFS is valid")
    credentials, _ = get_session_credentials(role_arn, region_name)
    client: EFSClient = _get_efs_client(credentials)
    try:
        fs_exist = client.describe_file_systems(FileSystemId=fs_id)

        if len(fs_exist.get("FileSystems")) == 0:
            return False

        tag = next((item for item in fs_exist["FileSystems"][0]["Tags"] if item["Key"] == "ManagedBy"), None)

        if tag is None or tag["Value"] != "Vantage":
            return False

        return True
    except client.exceptions.FileSystemNotFound as err:
        logger.exception(f"Error checking efs: {str(err)}")
        return False


def delete_efs(fs_id: str, role_arn: str, region_name: str) -> Literal[True, False]:
    """Delete an EFS."""
    logger.debug("Deleting EFS")
    credentials, _ = get_session_credentials(role_arn, region_name)
    client: EFSClient = _get_efs_client(credentials)

    try:
        fs_exist = client.describe_file_systems(FileSystemId=fs_id)
    except client.exceptions.FileSystemNotFound:
        return False
    else:
        if len(fs_exist.get("FileSystems")) == 0:
            return False

    tag = next((item for item in fs_exist["FileSystems"][0]["Tags"] if item["Key"] == "ManagedBy"), None)

    if tag is None or tag["Value"] != "Vantage":
        return False

    describe_mount_targets_paginator: DescribeMountTargetsPaginator = client.get_paginator(
        "describe_mount_targets"
    )
    for page in describe_mount_targets_paginator.paginate(FileSystemId=fs_id):
        for mount_target in page["MountTargets"]:
            client.delete_mount_target(MountTargetId=mount_target["MountTargetId"])

    client.delete_file_system(FileSystemId=fs_id)
    return True


def check_mount_point_path(aws_config: AwsOpsConfig, path: str, instance_id: str) -> bool:
    """Check if the given mount point is valid."""
    commands = ["df --output=target"]

    if path in ["/nfs", "/nfs/", "/nfs/slurm", "/nfs/slurm/"]:
        return False

    assert isinstance(aws_config["region_name"], str)
    session_credentials, _ = get_session_credentials(
        role_arn=aws_config["role_arn"], region_name=aws_config["region_name"]
    )

    ssm = _get_ssm_client(session_credentials)

    command_response = ssm.send_command(
        DocumentName="AWS-RunShellScript",
        Parameters={"commands": commands, "executionTimeout": ["15"]},
        InstanceIds=[instance_id],
    )

    time.sleep(2)
    command_output = _wait_command(
        ssm=ssm, command_id=command_response["Command"]["CommandId"], instance_id=instance_id
    )

    stdout = command_output["StandardOutputContent"]

    if not stdout:
        logger.debug(
            f"""Was not possible to check the given mount path.
                     Command returned with status: {command_output['Status']};
                     Stdout: {command_output['StandardOutputContent']};
                     Stderr: {command_output['StandardErrorContent']}.
                     """
        )
        logger.debug(command_output)
        return False
    used_paths = stdout.split("\n")

    if path in used_paths:
        logger.debug(
            f"The given mount point {path} is not valid. It's already in use. Used  paths: {used_paths}"
        )
        return False

    return True


def _wait_command(ssm: SSMClient, command_id: str, instance_id: str, time_out: int = 20):
    """Wait for the command to finish to run in the instance."""
    current_time = 0
    command_output = ssm.get_command_invocation(
        CommandId=command_id,
        InstanceId=instance_id,
    )

    while command_output["Status"] in ["Pending", "InProgress", "Delayed"]:
        logger.debug(f"Waiting command whose id is {command_id}.")
        command_output = ssm.get_command_invocation(
            CommandId=command_id,
            InstanceId=instance_id,
        )
        if current_time > time_out:
            command_output["Status"] = "TimedOut"
            return command_output
        current_time += 2
        time.sleep(2)

    return command_output


async def _subnet_id_list_async_generator(subnets: list[str]) -> AsyncGenerator[str, None]:
    for subnet in subnets:
        yield subnet


async def _create_mount_targets(
    efs: EFSClient,
    fs_id: str,
    subnets: list[str],
    security_group_id: str,
) -> bool | None:
    """Create the mount targets."""
    mount_targets = efs.describe_mount_targets(FileSystemId=fs_id)

    if len(mount_targets.get("MountTargets")) > 0:
        return None

    async for subnet in _subnet_id_list_async_generator(subnets):
        mount_target = efs.create_mount_target(
            FileSystemId=fs_id, SubnetId=subnet, SecurityGroups=[security_group_id]
        )

        status = _wait_mount_target(
            efs=efs,
            fs_id=fs_id,
            mount_target_id=mount_target["MountTargetId"],
        )

        if status != "available":
            logger.debug(
                f"""Mount Target not available: was not possible
                mount the storage {fs_id} because the mount target
                {mount_target['MountTargetId']} is not ready or it fails"""
            )
            return False

    return True


async def mount_storage(
    credentials: Dict[str, Union[str, Enum]],
    path: str,
    instance_id: str,
    storage_id: str,
    public_subnet_id: str,
    private_subnet_id: str,
    vpc_id: str,
):
    """Mount the storage into the instance."""
    mount_command = [
        f"mkdir -p {path}",
        f"until nc -z -w 2 {storage_id}.efs.{credentials['region_name']}.amazonaws.com 2049; do sleep 2; done;",  # noqa
        f"sudo mount -t efs -o tls {storage_id}:/ {path}",
        f"sudo chown -R ubuntu:ubuntu {path}",
        f"echo 'storage {storage_id} mounted in {path}'",
    ]
    session_credentials, _ = get_session_credentials(
        role_arn=credentials["role_arn"], region_name=credentials["region_name"]
    )

    ssm = _get_ssm_client(session_credentials)

    efs = _get_efs_client(session_credentials)
    ec2 = get_ec2_client(session_credentials)
    security_group = None
    try:
        security_group = ec2.create_security_group(
            GroupName=storage_id,
            VpcId=vpc_id,
            Description=f"Security group to allow access to the {storage_id} EFS",
            TagSpecifications=[
                {"ResourceType": "security-group", "Tags": [{"Key": "ManagedBy", "Value": "Vantage"}]}
            ],
        )

        ec2.authorize_security_group_ingress(
            GroupId=security_group["GroupId"],
            IpPermissions=[
                {
                    "IpProtocol": "tcp",
                    "FromPort": 2049,
                    "ToPort": 2049,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                },
            ],
        )

        mount_targets_created = await _create_mount_targets(
            efs, storage_id, [public_subnet_id, private_subnet_id], security_group["GroupId"]
        )
        if mount_targets_created is False or None:
            return False

        logger.debug(f"Storage {storage_id} mounted in {path}")

    except Exception:
        return False

    command_response = ssm.send_command(
        DocumentName="AWS-RunShellScript",
        Parameters={"commands": mount_command, "executionTimeout": ["120"]},
        InstanceIds=[instance_id],
    )

    time.sleep(2)
    command_output = _wait_command(
        ssm=ssm, command_id=command_response["Command"]["CommandId"], instance_id=instance_id, time_out=120
    )

    if command_output["Status"] != "Success":
        logger.error(f"Error while mounting the efs {str(command_output)}")
        return False

    try:
        logger.debug(
            "Tagging the instance {} with {}".format(instance_id, {f"mount-target/{storage_id}": {path}})
        )
        tag_instance(
            instance_id=instance_id,
            tags={f"mount-target/{storage_id}": path},
            credentials=session_credentials,
        )
    except Exception as e:
        logger.exception(f"Error tagging instance {instance_id}: {e}")
        return False

    return True


def umount_storage(path: str, instance_id: str, fs_id: str, vpc_id: str, aws_config: AwsOpsConfig):
    """Umount the storage from the instance."""
    role_arn = aws_config.get("role_arn")
    region_name = aws_config.get("region_name")
    assert role_arn is not None
    assert region_name is not None and isinstance(region_name, str)  # mypy purposes
    umount_command = [f"sudo umount {path}"]
    session_credentials, _ = get_session_credentials(role_arn=role_arn, region_name=region_name)

    ssm = _get_ssm_client(session_credentials)

    efs = _get_efs_client(session_credentials)
    ec2 = get_ec2_client(session_credentials)

    sgs = ec2.describe_security_groups(
        Filters=[
            {
                "Name": "vpc-id",
                "Values": [vpc_id],
            },
            {
                "Name": "group-name",
                "Values": [fs_id],
            },
            {
                "Name": "tag:ManagedBy",
                "Values": ["Vantage"],
            },
        ],
    )

    command_response = ssm.send_command(
        DocumentName="AWS-RunShellScript",
        Parameters={"commands": umount_command, "executionTimeout": ["19"]},
        InstanceIds=[instance_id],
    )

    time.sleep(2)
    command_output = _wait_command(
        ssm=ssm, command_id=command_response["Command"]["CommandId"], instance_id=instance_id
    )
    if (
        command_output["Status"] != "Success"
        and command_output["StandardErrorContent"] is not None
        and "mountpoint not found" not in command_output["StandardErrorContent"]
        and "not mounted" not in command_output["StandardErrorContent"]
    ):
        logger.error(f"Fail to unmount the storage {fs_id} from instance {instance_id}")
        logger.debug(command_output)
        return False

    mount_targets_response = efs.describe_mount_targets(FileSystemId=fs_id)
    mount_targets = mount_targets_response.get("MountTargets")

    try:
        assert mount_targets is not None
        if len(mount_targets) > 0:
            for mount_target in mount_targets:
                efs.delete_mount_target(MountTargetId=mount_target["MountTargetId"])

                status = _wait_mount_target(
                    fs_id=fs_id,
                    mount_target_id=mount_target["MountTargetId"],
                    efs=efs,
                )

                if status != "deleted":
                    logger.error(f"Fail to delete MountTarget {mount_target['MountTargetId']} from {fs_id}")
                    return False
    except Exception as e:
        logger.exception(
            f"Error deleting efs mount_target whose id is {mount_target['MountTargetId']} from file system {fs_id}: {e}"  # noqa
        )
        return False

    try:
        if len(sgs["SecurityGroups"]) > 0:
            ec2.delete_security_group(GroupId=sgs["SecurityGroups"][0]["GroupId"])
    except Exception as e:
        logger.exception(f"Error deleting efs security group: {e}")
        return False

    try:
        untag_instance(instance_id, {f"mount-target/{fs_id}": path}, session_credentials)
    except Exception as e:
        logger.exception(f"Error untagging instance {instance_id}: {e}")
        return False

    return True
