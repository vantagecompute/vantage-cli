"""Test the check path function."""
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
@mock.patch("api.efs_app.efs_ops._get_ssm_client")
@mock.patch("api.efs_app.efs_ops._wait_command")
def test_check_path__check_failure_when_path_is_system_protected(
    mocked_wait_command: mock.Mock,
    mocked_get_ssm_client: mock.Mock,
    mocked_get_session_credentials: mock.Mock,
    fs_id: str,
    fs_name: str,
    role_arn: str,
    region_name: str,
    owner_id: str,
    vpc_id: str,
):
    """Test if the check path will return false when the path is one of the protected system paths."""
    path = "/nfs/"
    instance_id = "instance_id"
    dummy_credentials = {
        "aws_access_key_id": "test-access-key",
        "aws_secret_access_key": "test-secret-key",
        "aws_session_token": "test-session-token",
    }
    ssm = botocore.session.get_session().create_client("ssm")
    ssm_stubber = Stubber(ssm)

    mocked_get_session_credentials.return_value = (dummy_credentials, None)

    ssm_stubber.activate()
    response = efs_ops.check_mount_point_path(
        aws_config={"role_arn": role_arn, "region_name": region_name},
        path=path,
        instance_id=instance_id,
    )
    ssm_stubber.deactivate()

    assert response is False
    mocked_get_session_credentials.assert_not_called()


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
@mock.patch("api.efs_app.efs_ops._get_ssm_client")
@mock.patch("api.efs_app.efs_ops._wait_command")
def test_check_path__check_failure_when_the_path_is_not_valid(
    mocked_wait_command: mock.Mock,
    mocked_get_ssm_client: mock.Mock,
    mocked_get_session_credentials: mock.Mock,
    fs_id: str,
    fs_name: str,
    role_arn: str,
    region_name: str,
    owner_id: str,
    vpc_id: str,
):
    """Test if the check path will return false when the path is not valid."""
    path = "/nfs/foo"
    instance_id = "instance_id"
    command_id = "super_dummy_command_id_to_meet_the_length_requirement_36"
    check_command = ["df --output=target"]
    dummy_credentials = {
        "aws_access_key_id": "test-access-key",
        "aws_secret_access_key": "test-secret-key",
        "aws_session_token": "test-session-token",
    }
    ssm = botocore.session.get_session().create_client("ssm")
    ssm_stubber = Stubber(ssm)

    ssm_stubber.add_response(
        method="send_command",
        expected_params={
            "DocumentName": "AWS-RunShellScript",
            "Parameters": {"commands": check_command, "executionTimeout": ["15"]},
            "InstanceIds": [instance_id],
        },
        service_response={"Command": {"CommandId": command_id}},
    )

    mocked_get_session_credentials.return_value = (dummy_credentials, None)
    mocked_wait_command.return_value = {
        "Status": "Failure",
        "StandardErrorContent": "unknown error",
        "StandardOutputContent": "",
    }
    mocked_get_ssm_client.return_value = ssm

    ssm_stubber.activate()
    response = efs_ops.check_mount_point_path(
        aws_config={"role_arn": role_arn, "region_name": region_name},
        path=path,
        instance_id=instance_id,
    )
    ssm_stubber.deactivate()

    assert response is False
    mocked_wait_command.assert_called_once_with(ssm=ssm, command_id=command_id, instance_id=instance_id)


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
@mock.patch("api.efs_app.efs_ops._get_ssm_client")
@mock.patch("api.efs_app.efs_ops._wait_command")
def test_check_path__check_when_path_is_in_use(
    mocked_wait_command: mock.Mock,
    mocked_get_ssm_client: mock.Mock,
    mocked_get_session_credentials: mock.Mock,
    fs_id: str,
    fs_name: str,
    role_arn: str,
    region_name: str,
    owner_id: str,
    vpc_id: str,
):
    """Test if the check path will return false when the path is in use by the instance."""
    path = "/nfs/foo"
    instance_id = "instance_id"
    command_id = "super_dummy_command_id_to_meet_the_length_requirement_36"
    check_command = ["df --output=target"]
    dummy_credentials = {
        "aws_access_key_id": "test-access-key",
        "aws_secret_access_key": "test-secret-key",
        "aws_session_token": "test-session-token",
    }
    ssm = botocore.session.get_session().create_client("ssm")
    ssm_stubber = Stubber(ssm)

    ssm_stubber.add_response(
        method="send_command",
        expected_params={
            "DocumentName": "AWS-RunShellScript",
            "Parameters": {"commands": check_command, "executionTimeout": ["15"]},
            "InstanceIds": [instance_id],
        },
        service_response={"Command": {"CommandId": command_id}},
    )

    mocked_get_session_credentials.return_value = (dummy_credentials, None)
    mocked_wait_command.return_value = {
        "Status": "Failure",
        "StandardErrorContent": "unknown error",
        "StandardOutputContent": "/nfs/foo\n/temp\n/mnt/disk",
    }
    mocked_get_ssm_client.return_value = ssm

    ssm_stubber.activate()
    response = efs_ops.check_mount_point_path(
        aws_config={"role_arn": role_arn, "region_name": region_name},
        path=path,
        instance_id=instance_id,
    )
    ssm_stubber.deactivate()

    assert response is False
    mocked_wait_command.assert_called_once_with(ssm=ssm, command_id=command_id, instance_id=instance_id)


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
@mock.patch("api.efs_app.efs_ops._get_ssm_client")
@mock.patch("api.efs_app.efs_ops._wait_command")
def test_check_path__check_when_path_is_not_in_user(
    mocked_wait_command: mock.Mock,
    mocked_get_ssm_client: mock.Mock,
    mocked_get_session_credentials: mock.Mock,
    fs_id: str,
    fs_name: str,
    role_arn: str,
    region_name: str,
    owner_id: str,
    vpc_id: str,
):
    """Test if the check path will return true when the path is available to mount."""
    path = "/nfs/foo"
    instance_id = "instance_id"
    command_id = "super_dummy_command_id_to_meet_the_length_requirement_36"
    check_command = ["df --output=target"]
    dummy_credentials = {
        "aws_access_key_id": "test-access-key",
        "aws_secret_access_key": "test-secret-key",
        "aws_session_token": "test-session-token",
    }
    ssm = botocore.session.get_session().create_client("ssm")
    ssm_stubber = Stubber(ssm)

    ssm_stubber.add_response(
        method="send_command",
        expected_params={
            "DocumentName": "AWS-RunShellScript",
            "Parameters": {"commands": check_command, "executionTimeout": ["15"]},
            "InstanceIds": [instance_id],
        },
        service_response={"Command": {"CommandId": command_id}},
    )

    mocked_get_session_credentials.return_value = (dummy_credentials, None)
    mocked_wait_command.return_value = {
        "Status": "Failure",
        "StandardErrorContent": "unknown error",
        "StandardOutputContent": "/nfs/test\n/temp\n/mnt/disk",
    }
    mocked_get_ssm_client.return_value = ssm

    ssm_stubber.activate()
    response = efs_ops.check_mount_point_path(
        aws_config={"role_arn": role_arn, "region_name": region_name},
        path=path,
        instance_id=instance_id,
    )
    ssm_stubber.deactivate()

    assert response is True
    mocked_wait_command.assert_called_once_with(ssm=ssm, command_id=command_id, instance_id=instance_id)
