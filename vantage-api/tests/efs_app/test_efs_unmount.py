"""Test cases for the efs_app.efs_ops.umount_storage function."""
from unittest import mock

import botocore.session
import pytest
from botocore.stub import Stubber

from api.efs_app import efs_ops


@pytest.mark.parametrize(
    "fs_id,fs_name,role_arn,region_name,owner_id,vpc_id",
    [
        (
            "fs-a1",
            "dummy-1",
            "arn:aws:iam::111111111111:role/test-1",
            "us-east-1",
            "111111111111",
            "vpc_id_a1",
        ),
        (
            "fs-b2",
            "dummy-2",
            "arn:aws:iam::222222222222:role/test-2",
            "us-west-2",
            "222222222222",
            "vpc_id_b2",
        ),
        (
            "fs-c3",
            "dummy-3",
            "arn:aws:iam::333333333333:role/test-3",
            "eu-north-1",
            "333333333333",
            "vpc_id_c3",
        ),
    ],
)
@mock.patch("api.efs_app.efs_ops.get_session_credentials")
@mock.patch("api.efs_app.efs_ops._get_efs_client")
@mock.patch("api.efs_app.efs_ops._get_ssm_client")
@mock.patch("api.efs_app.efs_ops.get_ec2_client")
@mock.patch("api.efs_app.efs_ops._wait_command")
def test_unmount_efs__check_failure_when_unmount_command_fails(
    mocked_wait_command: mock.Mock,
    mocked_get_ec2_client: mock.Mock,
    mocked_get_ssm_client: mock.Mock,
    mocked_get_efs_client: mock.Mock,
    mocked_get_session_credentials: mock.Mock,
    fs_id: str,
    fs_name: str,
    role_arn: str,
    region_name: str,
    owner_id: str,
    vpc_id: str,
):
    """Test if the unmount file system fails when an error occur during the unmount command."""
    sg_id = "sg-903004f8"
    path = "/nfs/foo"
    instance_id = "instance_id"
    command_id = "super_dummy_command_id_to_meet_the_length_requirement_36"
    umount_command = [f"sudo umount {path}"]
    dummy_credentials = {
        "aws_access_key_id": "test-access-key",
        "aws_secret_access_key": "test-secret-key",
        "aws_session_token": "test-session-token",
    }
    efs = mock.Mock()
    efs.delete_mount_target = mock.Mock()
    ec2 = botocore.session.get_session().create_client("ec2")
    ssm = botocore.session.get_session().create_client("ssm")
    ec2_stubber = Stubber(ec2)
    ssm_stubber = Stubber(ssm)

    ec2_stubber.add_response(
        method="describe_security_groups",
        service_response={
            "SecurityGroups": [{"GroupId": sg_id}],
            "ResponseMetadata": {
                "...": "...",
            },
        },
        expected_params={
            "Filters": [
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
        },
    )

    ssm_stubber.add_response(
        method="send_command",
        expected_params={
            "DocumentName": "AWS-RunShellScript",
            "Parameters": {"commands": umount_command, "executionTimeout": ["19"]},
            "InstanceIds": [instance_id],
        },
        service_response={
            "Command": {
                "CommandId": command_id,
            }
        },
    )

    mocked_get_session_credentials.return_value = (dummy_credentials, None)
    mocked_wait_command.return_value = {
        "Status": "Failure",
        "StandardErrorContent": "unknown error",
    }
    mocked_get_efs_client.return_value = efs
    mocked_get_ec2_client.return_value = ec2
    mocked_get_ssm_client.return_value = ssm

    ec2_stubber.activate()
    ssm_stubber.activate()
    response = efs_ops.umount_storage(
        aws_config={"role_arn": role_arn, "region_name": region_name},
        path=path,
        instance_id=instance_id,
        fs_id=fs_id,
        vpc_id=vpc_id,
    )
    ec2_stubber.deactivate()
    ssm_stubber.deactivate()

    assert response is False
    efs.delete_mount_target.assert_not_called()


@pytest.mark.parametrize(
    "fs_id,fs_name,role_arn,region_name,owner_id,vpc_id",
    [
        (
            "fs-a1",
            "dummy-1",
            "arn:aws:iam::111111111111:role/test-1",
            "us-east-1",
            "111111111111",
            "vpc_id_a1",
        ),
        (
            "fs-b2",
            "dummy-2",
            "arn:aws:iam::222222222222:role/test-2",
            "us-west-2",
            "222222222222",
            "vpc_id_b2",
        ),
        (
            "fs-c3",
            "dummy-3",
            "arn:aws:iam::333333333333:role/test-3",
            "eu-north-1",
            "333333333333",
            "vpc_id_c3",
        ),
    ],
)
@mock.patch("api.efs_app.efs_ops.get_session_credentials")
@mock.patch("api.efs_app.efs_ops._get_efs_client")
@mock.patch("api.efs_app.efs_ops._get_ssm_client")
@mock.patch("api.efs_app.efs_ops.get_ec2_client")
@mock.patch("api.efs_app.efs_ops._wait_command")
@mock.patch("api.efs_app.efs_ops._wait_mount_target")
def test_unmount_efs__check_failure_when_deleting_mount_targets(
    mocked_wait_mount_target: mock.Mock,
    mocked_wait_command: mock.Mock,
    mocked_get_ec2_client: mock.Mock,
    mocked_get_ssm_client: mock.Mock,
    mocked_get_efs_client: mock.Mock,
    mocked_get_session_credentials: mock.Mock,
    fs_id: str,
    fs_name: str,
    role_arn: str,
    region_name: str,
    owner_id: str,
    vpc_id: str,
):
    """Test if the unmount file system fails when is not possible to delete the mount target."""
    sg_id = "sg-903004f8"
    path = "/nfs/foo"
    instance_id = "instance_id"
    mount_target_id = "fsmt-12340abc"
    command_id = "super_dummy_command_id_to_meet_the_length_requirement_36"
    umount_command = [f"sudo umount {path}"]
    dummy_credentials = {
        "aws_access_key_id": "test-access-key",
        "aws_secret_access_key": "test-secret-key",
        "aws_session_token": "test-session-token",
    }
    ec2 = botocore.session.get_session().create_client("ec2")
    ssm = botocore.session.get_session().create_client("ssm")
    efs = botocore.session.get_session().create_client("efs")
    ec2_stubber = Stubber(ec2)
    efs_stubber = Stubber(efs)
    ssm_stubber = Stubber(ssm)

    ec2_stubber.add_response(
        method="describe_security_groups",
        service_response={
            "SecurityGroups": [{"GroupId": sg_id}],
            "ResponseMetadata": {
                "...": "...",
            },
        },
        expected_params={
            "Filters": [
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
        },
    )

    ssm_stubber.add_response(
        method="send_command",
        expected_params={
            "DocumentName": "AWS-RunShellScript",
            "Parameters": {"commands": umount_command, "executionTimeout": ["19"]},
            "InstanceIds": [instance_id],
        },
        service_response={
            "Command": {
                "CommandId": command_id,
            }
        },
    )

    efs_stubber.add_response(
        method="describe_mount_targets",
        expected_params={"FileSystemId": fs_id},
        service_response={
            "MountTargets": [
                {
                    "OwnerId": owner_id,
                    "MountTargetId": mount_target_id,
                    "FileSystemId": fs_id,
                    "SubnetId": "subnet-subnetId",
                    "LifeCycleState": "available",
                    "VpcId": vpc_id,
                },
            ],
        },
    )
    efs_stubber.add_client_error(
        method="delete_mount_target",
        expected_params={"MountTargetId": mount_target_id},
        service_error_code="StubResponseError",
    )

    mocked_get_session_credentials.return_value = (dummy_credentials, None)
    mocked_wait_command.return_value = {
        "Status": "Success",
    }
    mocked_get_efs_client.return_value = efs
    mocked_get_ec2_client.return_value = ec2
    mocked_get_ssm_client.return_value = ssm

    ec2_stubber.activate()
    ssm_stubber.activate()
    efs_stubber.activate()
    response = efs_ops.umount_storage(
        aws_config={"role_arn": role_arn, "region_name": region_name},
        path=path,
        instance_id=instance_id,
        fs_id=fs_id,
        vpc_id=vpc_id,
    )
    ec2_stubber.deactivate()
    ssm_stubber.deactivate()
    efs_stubber.deactivate()

    assert response is False
    mocked_wait_command.assert_called_once_with(ssm=ssm, command_id=command_id, instance_id=instance_id)
    mocked_wait_mount_target.assert_not_called()


@pytest.mark.parametrize(
    "fs_id,fs_name,role_arn,region_name,owner_id,vpc_id",
    [
        (
            "fs-a1",
            "dummy-1",
            "arn:aws:iam::111111111111:role/test-1",
            "us-east-1",
            "111111111111",
            "vpc_id_a1",
        ),
        (
            "fs-b2",
            "dummy-2",
            "arn:aws:iam::222222222222:role/test-2",
            "us-west-2",
            "222222222222",
            "vpc_id_b2",
        ),
        (
            "fs-c3",
            "dummy-3",
            "arn:aws:iam::333333333333:role/test-3",
            "eu-north-1",
            "333333333333",
            "vpc_id_c3",
        ),
    ],
)
@mock.patch("api.efs_app.efs_ops.get_session_credentials")
@mock.patch("api.efs_app.efs_ops._get_efs_client")
@mock.patch("api.efs_app.efs_ops._get_ssm_client")
@mock.patch("api.efs_app.efs_ops.get_ec2_client")
@mock.patch("api.efs_app.efs_ops._wait_command")
@mock.patch("api.efs_app.efs_ops._wait_mount_target")
def test_unmount_efs__check_failure_when_waiting_for_mount_target_deletion(
    mocked_wait_mount_target: mock.Mock,
    mocked_wait_command: mock.Mock,
    mocked_get_ec2_client: mock.Mock,
    mocked_get_ssm_client: mock.Mock,
    mocked_get_efs_client: mock.Mock,
    mocked_get_session_credentials: mock.Mock,
    fs_id: str,
    fs_name: str,
    role_arn: str,
    region_name: str,
    owner_id: str,
    vpc_id: str,
):
    """Test if the unmount file system fails when some error occur during the mount target deletion."""
    sg_id = "sg-903004f8"
    path = "/nfs/foo"
    instance_id = "instance_id"
    mount_target_id = "fsmt-12340abc"
    command_id = "super_dummy_command_id_to_meet_the_length_requirement_36"
    umount_command = [f"sudo umount {path}"]
    dummy_credentials = {
        "aws_access_key_id": "test-access-key",
        "aws_secret_access_key": "test-secret-key",
        "aws_session_token": "test-session-token",
    }
    ec2 = botocore.session.get_session().create_client("ec2")
    ssm = botocore.session.get_session().create_client("ssm")
    efs = botocore.session.get_session().create_client("efs")
    ec2_stubber = Stubber(ec2)
    efs_stubber = Stubber(efs)
    ssm_stubber = Stubber(ssm)

    ec2_stubber.add_response(
        method="describe_security_groups",
        service_response={
            "SecurityGroups": [{"GroupId": sg_id}],
            "ResponseMetadata": {
                "...": "...",
            },
        },
        expected_params={
            "Filters": [
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
        },
    )

    ssm_stubber.add_response(
        method="send_command",
        expected_params={
            "DocumentName": "AWS-RunShellScript",
            "Parameters": {"commands": umount_command, "executionTimeout": ["19"]},
            "InstanceIds": [instance_id],
        },
        service_response={
            "Command": {
                "CommandId": command_id,
            }
        },
    )

    efs_stubber.add_response(
        method="describe_mount_targets",
        expected_params={"FileSystemId": fs_id},
        service_response={
            "MountTargets": [
                {
                    "OwnerId": owner_id,
                    "MountTargetId": mount_target_id,
                    "FileSystemId": fs_id,
                    "SubnetId": "subnet-subnetId",
                    "LifeCycleState": "available",
                    "VpcId": vpc_id,
                },
            ],
        },
    )
    efs_stubber.add_response(
        method="delete_mount_target",
        expected_params={"MountTargetId": mount_target_id},
        service_response={
            "ResponseMetadata": {
                "...": "...",
            },
        },
    )

    mocked_get_session_credentials.return_value = (dummy_credentials, None)
    mocked_wait_command.return_value = {
        "Status": "Success",
    }
    mocked_wait_mount_target.return_value = "error"
    mocked_get_efs_client.return_value = efs
    mocked_get_ec2_client.return_value = ec2
    mocked_get_ssm_client.return_value = ssm

    ec2_stubber.activate()
    ssm_stubber.activate()
    efs_stubber.activate()
    response = efs_ops.umount_storage(
        aws_config={"role_arn": role_arn, "region_name": region_name},
        path=path,
        instance_id=instance_id,
        fs_id=fs_id,
        vpc_id=vpc_id,
    )
    ec2_stubber.deactivate()
    ssm_stubber.deactivate()
    efs_stubber.deactivate()

    assert response is False
    mocked_wait_command.assert_called_once_with(ssm=ssm, command_id=command_id, instance_id=instance_id)
    mocked_wait_mount_target.assert_called_once_with(
        fs_id=fs_id,
        mount_target_id=mount_target_id,
        efs=efs,
    )


@pytest.mark.parametrize(
    "fs_id,fs_name,role_arn,region_name,owner_id,vpc_id",
    [
        (
            "fs-a1",
            "dummy-1",
            "arn:aws:iam::111111111111:role/test-1",
            "us-east-1",
            "111111111111",
            "vpc_id_a1",
        ),
        (
            "fs-b2",
            "dummy-2",
            "arn:aws:iam::222222222222:role/test-2",
            "us-west-2",
            "222222222222",
            "vpc_id_b2",
        ),
        (
            "fs-c3",
            "dummy-3",
            "arn:aws:iam::333333333333:role/test-3",
            "eu-north-1",
            "333333333333",
            "vpc_id_c3",
        ),
    ],
)
@mock.patch("api.efs_app.efs_ops.get_session_credentials")
@mock.patch("api.efs_app.efs_ops._get_efs_client")
@mock.patch("api.efs_app.efs_ops._get_ssm_client")
@mock.patch("api.efs_app.efs_ops.get_ec2_client")
@mock.patch("api.efs_app.efs_ops._wait_command")
@mock.patch("api.efs_app.efs_ops._wait_mount_target")
def test_unmount_efs__check_failure_when_deleting_security_group(
    mocked_wait_mount_target: mock.Mock,
    mocked_wait_command: mock.Mock,
    mocked_get_ec2_client: mock.Mock,
    mocked_get_ssm_client: mock.Mock,
    mocked_get_efs_client: mock.Mock,
    mocked_get_session_credentials: mock.Mock,
    fs_id: str,
    fs_name: str,
    role_arn: str,
    region_name: str,
    owner_id: str,
    vpc_id: str,
):
    """Test if the unmount file system fails when some error occur security group deletion."""
    sg_id = "sg-903004f8"
    path = "/nfs/foo"
    instance_id = "instance_id"
    mount_target_id = "fsmt-12340abc"
    command_id = "super_dummy_command_id_to_meet_the_length_requirement_36"
    umount_command = [f"sudo umount {path}"]
    dummy_credentials = {
        "aws_access_key_id": "test-access-key",
        "aws_secret_access_key": "test-secret-key",
        "aws_session_token": "test-session-token",
    }
    ec2 = botocore.session.get_session().create_client("ec2")
    ssm = botocore.session.get_session().create_client("ssm")
    efs = botocore.session.get_session().create_client("efs")
    ec2_stubber = Stubber(ec2)
    efs_stubber = Stubber(efs)
    ssm_stubber = Stubber(ssm)

    ec2_stubber.add_response(
        method="describe_security_groups",
        service_response={
            "SecurityGroups": [{"GroupId": sg_id}],
            "ResponseMetadata": {
                "...": "...",
            },
        },
        expected_params={
            "Filters": [
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
        },
    )
    ec2_stubber.add_client_error(
        method="delete_security_group",
        expected_params={"GroupId": sg_id},
        service_error_code="StubResponseError",
    )

    ssm_stubber.add_response(
        method="send_command",
        expected_params={
            "DocumentName": "AWS-RunShellScript",
            "Parameters": {"commands": umount_command, "executionTimeout": ["19"]},
            "InstanceIds": [instance_id],
        },
        service_response={
            "Command": {
                "CommandId": command_id,
            }
        },
    )

    efs_stubber.add_response(
        method="describe_mount_targets",
        expected_params={"FileSystemId": fs_id},
        service_response={
            "MountTargets": [
                {
                    "OwnerId": owner_id,
                    "MountTargetId": mount_target_id,
                    "FileSystemId": fs_id,
                    "SubnetId": "subnet-subnetId",
                    "LifeCycleState": "available",
                    "VpcId": vpc_id,
                },
            ],
        },
    )
    efs_stubber.add_response(
        method="delete_mount_target",
        expected_params={"MountTargetId": mount_target_id},
        service_response={
            "ResponseMetadata": {
                "...": "...",
            },
        },
    )

    mocked_get_session_credentials.return_value = (dummy_credentials, None)
    mocked_wait_command.return_value = {
        "Status": "Success",
    }
    mocked_wait_mount_target.return_value = "deleted"
    mocked_get_efs_client.return_value = efs
    mocked_get_ec2_client.return_value = ec2
    mocked_get_ssm_client.return_value = ssm

    ec2_stubber.activate()
    ssm_stubber.activate()
    efs_stubber.activate()
    response = efs_ops.umount_storage(
        aws_config={"role_arn": role_arn, "region_name": region_name},
        path=path,
        instance_id=instance_id,
        fs_id=fs_id,
        vpc_id=vpc_id,
    )
    ec2_stubber.deactivate()
    ssm_stubber.deactivate()
    efs_stubber.deactivate()

    assert response is False
    mocked_wait_command.assert_called_once_with(ssm=ssm, command_id=command_id, instance_id=instance_id)
    mocked_wait_mount_target.assert_called_once_with(
        fs_id=fs_id,
        mount_target_id=mount_target_id,
        efs=efs,
    )


@pytest.mark.parametrize(
    "fs_id,fs_name,role_arn,region_name,owner_id,vpc_id",
    [
        (
            "fs-a1",
            "dummy-1",
            "arn:aws:iam::111111111111:role/test-1",
            "us-east-1",
            "111111111111",
            "vpc_id_a1",
        ),
        (
            "fs-b2",
            "dummy-2",
            "arn:aws:iam::222222222222:role/test-2",
            "us-west-2",
            "222222222222",
            "vpc_id_b2",
        ),
        (
            "fs-c3",
            "dummy-3",
            "arn:aws:iam::333333333333:role/test-3",
            "eu-north-1",
            "333333333333",
            "vpc_id_c3",
        ),
    ],
)
@mock.patch("api.efs_app.efs_ops.get_session_credentials")
@mock.patch("api.efs_app.efs_ops._get_efs_client")
@mock.patch("api.efs_app.efs_ops._get_ssm_client")
@mock.patch("api.efs_app.efs_ops.get_ec2_client")
@mock.patch("api.efs_app.efs_ops._wait_command")
@mock.patch("api.efs_app.efs_ops._wait_mount_target")
@mock.patch("api.efs_app.efs_ops.untag_instance")
def test_unmount_efs__check_failure_when_the_storage_is_unmounted_with_success(
    mocked_untag_instance: mock.MagicMock,
    mocked_wait_mount_target: mock.Mock,
    mocked_wait_command: mock.Mock,
    mocked_get_ec2_client: mock.Mock,
    mocked_get_ssm_client: mock.Mock,
    mocked_get_efs_client: mock.Mock,
    mocked_get_session_credentials: mock.Mock,
    fs_id: str,
    fs_name: str,
    role_arn: str,
    region_name: str,
    owner_id: str,
    vpc_id: str,
):
    """Test if the unmount file system is unmounted with success."""
    sg_id = "sg-903004f8"
    path = "/nfs/foo"
    instance_id = "instance_id"
    mount_target_id = "fsmt-12340abc"
    command_id = "super_dummy_command_id_to_meet_the_length_requirement_36"
    umount_command = [f"sudo umount {path}"]
    dummy_credentials = {
        "aws_access_key_id": "test-access-key",
        "aws_secret_access_key": "test-secret-key",
        "aws_session_token": "test-session-token",
    }
    ec2 = botocore.session.get_session().create_client("ec2")
    ssm = botocore.session.get_session().create_client("ssm")
    efs = botocore.session.get_session().create_client("efs")
    ec2_stubber = Stubber(ec2)
    efs_stubber = Stubber(efs)
    ssm_stubber = Stubber(ssm)

    ec2_stubber.add_response(
        method="describe_security_groups",
        service_response={
            "SecurityGroups": [{"GroupId": sg_id}],
            "ResponseMetadata": {
                "...": "...",
            },
        },
        expected_params={
            "Filters": [
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
        },
    )
    ec2_stubber.add_response(
        method="delete_security_group",
        expected_params={"GroupId": sg_id},
        service_response={
            "ResponseMetadata": {
                "...": "...",
            },
        },
    )

    ssm_stubber.add_response(
        method="send_command",
        expected_params={
            "DocumentName": "AWS-RunShellScript",
            "Parameters": {"commands": umount_command, "executionTimeout": ["19"]},
            "InstanceIds": [instance_id],
        },
        service_response={
            "Command": {
                "CommandId": command_id,
            }
        },
    )

    efs_stubber.add_response(
        method="describe_mount_targets",
        expected_params={"FileSystemId": fs_id},
        service_response={
            "MountTargets": [
                {
                    "OwnerId": owner_id,
                    "MountTargetId": mount_target_id,
                    "FileSystemId": fs_id,
                    "SubnetId": "subnet-subnetId",
                    "LifeCycleState": "available",
                    "VpcId": vpc_id,
                },
            ],
        },
    )
    efs_stubber.add_response(
        method="delete_mount_target",
        expected_params={"MountTargetId": mount_target_id},
        service_response={
            "ResponseMetadata": {
                "...": "...",
            },
        },
    )

    mocked_get_session_credentials.return_value = (dummy_credentials, None)
    mocked_wait_command.return_value = {
        "Status": "Success",
    }
    mocked_wait_mount_target.return_value = "deleted"
    mocked_get_efs_client.return_value = efs
    mocked_get_ec2_client.return_value = ec2
    mocked_get_ssm_client.return_value = ssm

    ec2_stubber.activate()
    ssm_stubber.activate()
    efs_stubber.activate()
    response = efs_ops.umount_storage(
        aws_config={"role_arn": role_arn, "region_name": region_name},
        path=path,
        instance_id=instance_id,
        fs_id=fs_id,
        vpc_id=vpc_id,
    )
    ec2_stubber.deactivate()
    ssm_stubber.deactivate()
    efs_stubber.deactivate()

    assert response is True
    mocked_wait_command.assert_called_once_with(ssm=ssm, command_id=command_id, instance_id=instance_id)
    mocked_wait_mount_target.assert_called_once_with(
        fs_id=fs_id,
        mount_target_id=mount_target_id,
        efs=efs,
    )
    mocked_untag_instance.assert_called_once_with(
        instance_id,
        {f"mount-target/{fs_id}": path},
        dummy_credentials,
    )
