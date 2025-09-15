"""Test cases for the EFS mount operations."""
from unittest import mock

import botocore.session
import pytest
from botocore.stub import Stubber

from api.efs_app import efs_ops


@pytest.mark.asyncio
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
async def test_mount_efs__check_failure_to_create_security_group(
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
    """Test if the mount file system fails when is not possible to create security group."""
    dummy_credentials = {
        "aws_access_key_id": "test-access-key",
        "aws_secret_access_key": "test-secret-key",
        "aws_session_token": "test-session-token",
    }
    efs = mock.Mock()
    efs.delete_mount_target = mock.Mock()
    ssm = mock.Mock()
    ec2 = botocore.session.get_session().create_client("ec2")
    ec2_stubber = Stubber(ec2)

    ec2_stubber.add_client_error(
        "create_security_group",
        service_error_code="StubResponseError",
        expected_params={
            "GroupName": fs_id,
            "VpcId": vpc_id,
            "Description": f"Security group to allow access to the {fs_id} EFS",
            "TagSpecifications": [
                {"ResourceType": "security-group", "Tags": [{"Key": "ManagedBy", "Value": "Vantage"}]}
            ],
        },
    )

    mocked_get_session_credentials.return_value = (dummy_credentials, None)
    mocked_get_efs_client.return_value = efs
    mocked_get_ec2_client.return_value = ec2
    mocked_get_ssm_client.return_value = ssm

    ec2_stubber.activate()
    response = await efs_ops.mount_storage(
        credentials={"role_arn": role_arn, "region_name": region_name},
        instance_id="i-instanceId",
        path="/nfs/foo",
        storage_id=fs_id,
        public_subnet_id="public-subnetId",
        private_subnet_id="private-subnetId",
        vpc_id="vpc-vpcId",
    )
    ec2_stubber.deactivate()

    assert response is False
    efs.delete_mount_target.assert_not_called()


@pytest.mark.asyncio
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
async def test_mount_efs__check_failure_to_authorize_security_group_ports(
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
    """Test if the mount file system fails when is not possible to create ingress rule in security group."""
    dummy_credentials = {
        "aws_access_key_id": "test-access-key",
        "aws_secret_access_key": "test-secret-key",
        "aws_session_token": "test-session-token",
    }
    sg_id = "sg-903004f8"
    efs = mock.Mock()
    efs.delete_mount_target = mock.Mock()
    ssm = mock.Mock()
    ec2 = botocore.session.get_session().create_client("ec2")
    ec2_stubber = Stubber(ec2)

    ec2_stubber.add_response(
        method="create_security_group",
        service_response={
            "GroupId": sg_id,
            "ResponseMetadata": {
                "...": "...",
            },
        },
        expected_params={
            "GroupName": fs_id,
            "VpcId": vpc_id,
            "Description": f"Security group to allow access to the {fs_id} EFS",
            "TagSpecifications": [
                {"ResourceType": "security-group", "Tags": [{"Key": "ManagedBy", "Value": "Vantage"}]}
            ],
        },
    )
    ec2_stubber.add_client_error(
        method="authorize_security_group_ingress", service_error_code="StubResponseError"
    )

    ec2_stubber.add_response(
        method="delete_security_group",
        service_response={
            "ResponseMetadata": {
                "...": "...",
            },
        },
        expected_params={
            "GroupId": sg_id,
        },
    )

    mocked_get_session_credentials.return_value = (dummy_credentials, None)
    mocked_get_efs_client.return_value = efs
    mocked_get_ec2_client.return_value = ec2
    mocked_get_ssm_client.return_value = ssm

    ec2_stubber.activate()
    response = await efs_ops.mount_storage(
        credentials={"role_arn": role_arn, "region_name": region_name},
        instance_id="i-instanceId",
        path="/nfs/foo",
        storage_id=fs_id,
        public_subnet_id="public-subnetId",
        private_subnet_id="private-subnetId",
        vpc_id=vpc_id,
    )
    ec2_stubber.deactivate()

    assert response is False
    efs.delete_mount_target.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fs_id,fs_name,role_arn,region_name,owner_id,vpc_id,subnet_id",
    [
        (
            "fs-a1",
            "dummy-1",
            "arn:aws:iam::111111111111:role/test-1",
            "us-east-1",
            "111111111111",
            "vpc_id_a1",
            "subnet_id_aaaa1",
        ),
        (
            "fs-b2",
            "dummy-2",
            "arn:aws:iam::222222222222:role/test-2",
            "us-west-2",
            "222222222222",
            "vpc_id_b2",
            "subnet_id_bbbb2",
        ),
        (
            "fs-c3",
            "dummy-3",
            "arn:aws:iam::333333333333:role/test-3",
            "eu-north-1",
            "333333333333",
            "vpc_id_c3",
            "subnet_id_cccc3",
        ),
    ],
)
@mock.patch("api.efs_app.efs_ops.get_session_credentials")
@mock.patch("api.efs_app.efs_ops._get_efs_client")
@mock.patch("api.efs_app.efs_ops._get_ssm_client")
@mock.patch("api.efs_app.efs_ops.get_ec2_client")
async def test_mount_efs__check_failure_to_create_mount_target(
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
    subnet_id: str,
):
    """Test if the mount file system fails when is not possible to create mount target."""
    sg_id = "sg-903004f8"
    dummy_credentials = {
        "aws_access_key_id": "test-access-key",
        "aws_secret_access_key": "test-secret-key",
        "aws_session_token": "test-session-token",
    }
    ssm = mock.Mock()
    ec2 = botocore.session.get_session().create_client("ec2")
    efs = botocore.session.get_session().create_client("efs")
    ec2_stubber = Stubber(ec2)
    efs_stubber = Stubber(efs)

    sg_response = {
        "GroupId": sg_id,
        "ResponseMetadata": {
            "...": "...",
        },
    }
    ec2_stubber.add_response(
        method="create_security_group",
        service_response=sg_response,
        expected_params={
            "GroupName": fs_id,
            "VpcId": vpc_id,
            "Description": f"Security group to allow access to the {fs_id} EFS",
            "TagSpecifications": [
                {"ResourceType": "security-group", "Tags": [{"Key": "ManagedBy", "Value": "Vantage"}]}
            ],
        },
    )
    ec2_stubber.add_response(
        method="authorize_security_group_ingress",
        service_response={
            "Return": True,
            "SecurityGroupRules": [
                {
                    "SecurityGroupRuleId": "RuleId",
                    "GroupId": sg_id,
                    "IsEgress": False,
                    "FromPort": 2049,
                    "ToPort": 2049,
                }
            ],
        },
        expected_params={
            "GroupId": sg_id,
            "IpPermissions": [
                {
                    "IpProtocol": "tcp",
                    "FromPort": 2049,
                    "ToPort": 2049,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                },
            ],
        },
    )
    ec2_stubber.add_response(
        method="delete_security_group",
        service_response={
            "ResponseMetadata": {
                "...": "...",
            },
        },
        expected_params={
            "GroupId": sg_id,
        },
    )

    efs_stubber.add_client_error(
        "create_mount_target",
        expected_params={
            "FileSystemId": fs_id,
            "SubnetId": subnet_id,
            "SecurityGroups": [sg_id],
        },
        service_error_code="StubResponseError",
    )

    mocked_get_session_credentials.return_value = (dummy_credentials, None)
    mocked_get_efs_client.return_value = efs
    mocked_get_ec2_client.return_value = ec2
    mocked_get_ssm_client.return_value = ssm

    ec2_stubber.activate()
    efs_stubber.activate()
    response = await efs_ops.mount_storage(
        credentials={"role_arn": role_arn, "region_name": region_name},
        instance_id="i-instanceId",
        path="/nfs/foo",
        storage_id=fs_id,
        public_subnet_id=subnet_id,
        private_subnet_id=subnet_id,
        vpc_id=vpc_id,
    )
    ec2_stubber.deactivate()
    efs_stubber.deactivate()

    assert response is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fs_id,fs_name,role_arn,region_name,owner_id,vpc_id,public_subnet_id,private_subnet_id",
    [
        (
            "fs-a1",
            "dummy-1",
            "arn:aws:iam::111111111111:role/test-1",
            "us-east-1",
            "111111111111",
            "vpc_id_a1",
            "subnet_id_aaaa1",
            "subnet_id_zzzz1",
        ),
        (
            "fs-b2",
            "dummy-2",
            "arn:aws:iam::222222222222:role/test-2",
            "us-west-2",
            "222222222222",
            "vpc_id_b2",
            "subnet_id_bbbb2",
            "subnet_id_yyyy2",
        ),
        (
            "fs-c3",
            "dummy-3",
            "arn:aws:iam::333333333333:role/test-3",
            "eu-north-1",
            "333333333333",
            "vpc_id_c3",
            "subnet_id_cccc3",
            "subnet_id_llll3",
        ),
    ],
)
@mock.patch("api.efs_app.efs_ops.get_session_credentials")
@mock.patch("api.efs_app.efs_ops._get_efs_client")
@mock.patch("api.efs_app.efs_ops._get_ssm_client")
@mock.patch("api.efs_app.efs_ops.get_ec2_client")
@mock.patch("api.efs_app.efs_ops._create_mount_targets")
async def test_mount_efs__check_failure_while_waiting_for_mount_target(
    mocked_create_mount_targets: mock.Mock,
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
    public_subnet_id: str,
    private_subnet_id: str,
):
    """Test if the mount file system fails when some error occur during the mount target creation."""
    sg_id = "sg-903004f8"
    mount_target_id = "fsmt-12340abc"
    dummy_credentials = {
        "aws_access_key_id": "test-access-key",
        "aws_secret_access_key": "test-secret-key",
        "aws_session_token": "test-session-token",
    }
    ssm = mock.Mock()
    ec2 = botocore.session.get_session().create_client("ec2")
    efs = botocore.session.get_session().create_client("efs")
    ec2_stubber = Stubber(ec2)
    efs_stubber = Stubber(efs)

    ec2_stubber.add_response(
        method="create_security_group",
        service_response={
            "GroupId": sg_id,
            "ResponseMetadata": {
                "...": "...",
            },
        },
        expected_params={
            "GroupName": fs_id,
            "VpcId": vpc_id,
            "Description": f"Security group to allow access to the {fs_id} EFS",
            "TagSpecifications": [
                {"ResourceType": "security-group", "Tags": [{"Key": "ManagedBy", "Value": "Vantage"}]}
            ],
        },
    )
    ec2_stubber.add_response(
        method="authorize_security_group_ingress",
        service_response={
            "Return": True,
            "SecurityGroupRules": [
                {
                    "SecurityGroupRuleId": "RuleId",
                    "GroupId": sg_id,
                    "IsEgress": False,
                    "FromPort": 2049,
                    "ToPort": 2049,
                }
            ],
        },
        expected_params={
            "GroupId": sg_id,
            "IpPermissions": [
                {
                    "IpProtocol": "tcp",
                    "FromPort": 2049,
                    "ToPort": 2049,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                },
            ],
        },
    )

    efs_stubber.add_response(
        method="create_mount_target",
        service_response={
            "FileSystemId": fs_id,
            "IpAddress": "192.0.0.2",
            "LifeCycleState": "creating",
            "MountTargetId": mount_target_id,
            "NetworkInterfaceId": "eni-cedf6789",
            "OwnerId": owner_id,
            "SubnetId": public_subnet_id,
            "ResponseMetadata": {
                "...": "...",
            },
        },
        expected_params={
            "FileSystemId": fs_id,
            "SubnetId": public_subnet_id,
            "SecurityGroups": [sg_id],
        },
    )

    mocked_get_session_credentials.return_value = (dummy_credentials, None)
    mocked_create_mount_targets.return_value = False
    mocked_get_efs_client.return_value = efs
    mocked_get_ec2_client.return_value = ec2
    mocked_get_ssm_client.return_value = ssm

    ec2_stubber.activate()
    efs_stubber.activate()
    response = await efs_ops.mount_storage(
        credentials={"role_arn": role_arn, "region_name": region_name},
        instance_id="i-instanceId",
        path="/nfs/foo",
        storage_id=fs_id,
        public_subnet_id=public_subnet_id,
        private_subnet_id=private_subnet_id,
        vpc_id=vpc_id,
    )
    ec2_stubber.deactivate()
    efs_stubber.deactivate()

    assert response is False
    mocked_create_mount_targets.assert_called_once_with(
        efs,
        fs_id,
        [public_subnet_id, private_subnet_id],
        sg_id,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fs_id,fs_name,role_arn,region_name,owner_id,vpc_id,subnet_id",
    [
        (
            "fs-a1",
            "dummy-1",
            "arn:aws:iam::111111111111:role/test-1",
            "us-east-1",
            "111111111111",
            "vpc_id_a1",
            "subnet_id_aaaa1",
        ),
        (
            "fs-b2",
            "dummy-2",
            "arn:aws:iam::222222222222:role/test-2",
            "us-west-2",
            "222222222222",
            "vpc_id_b2",
            "subnet_id_bbbb2",
        ),
        (
            "fs-c3",
            "dummy-3",
            "arn:aws:iam::333333333333:role/test-3",
            "eu-north-1",
            "333333333333",
            "vpc_id_c3",
            "subnet_id_cccc3",
        ),
    ],
)
@mock.patch("api.efs_app.efs_ops.get_session_credentials")
@mock.patch("api.efs_app.efs_ops._get_efs_client")
@mock.patch("api.efs_app.efs_ops._get_ssm_client")
@mock.patch("api.efs_app.efs_ops.get_ec2_client")
@mock.patch("api.efs_app.efs_ops._create_mount_targets")
@mock.patch("api.efs_app.efs_ops._wait_command")
async def test_mount_efs__check_failure_on_mount_command(
    mocked_wait_command: mock.Mock,
    mocked_create_mount_targets: mock.Mock,
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
    subnet_id: str,
):
    """Test if the mount file system fails when some error occur during the mount target command."""
    sg_id = "sg-903004f8"
    mount_target_id = "fsmt-12340abc"
    instance_id = "instance_id"
    path = "/nfs/foo"
    command_id = "super_dummy_command_id_to_meet_the_length_requirement_36"
    dummy_credentials = {
        "aws_access_key_id": "test-access-key",
        "aws_secret_access_key": "test-secret-key",
        "aws_session_token": "test-session-token",
    }
    mount_command = [
        f"mkdir -p {path}",
        f"until nc -z -w 2 {fs_id}.efs.{region_name}.amazonaws.com 2049; do sleep 2; done;",
        f"sudo mount -t efs -o tls {fs_id}:/ {path}",
        f"sudo chown -R ubuntu:ubuntu {path}",
        f"echo 'storage {fs_id} mounted in {path}'",
    ]

    ec2 = botocore.session.get_session().create_client("ec2")
    efs = botocore.session.get_session().create_client("efs")
    ssm = botocore.session.get_session().create_client("ssm")
    ec2_stubber = Stubber(ec2)
    efs_stubber = Stubber(efs)
    ssm_stubber = Stubber(ssm)

    ec2_stubber.add_response(
        method="create_security_group",
        service_response={
            "GroupId": sg_id,
            "ResponseMetadata": {
                "...": "...",
            },
        },
        expected_params={
            "GroupName": fs_id,
            "VpcId": vpc_id,
            "Description": f"Security group to allow access to the {fs_id} EFS",
            "TagSpecifications": [
                {"ResourceType": "security-group", "Tags": [{"Key": "ManagedBy", "Value": "Vantage"}]}
            ],
        },
    )
    ec2_stubber.add_response(
        method="authorize_security_group_ingress",
        service_response={
            "Return": True,
            "SecurityGroupRules": [
                {
                    "SecurityGroupRuleId": "RuleId",
                    "GroupId": sg_id,
                    "IsEgress": False,
                    "FromPort": 2049,
                    "ToPort": 2049,
                }
            ],
        },
        expected_params={
            "GroupId": sg_id,
            "IpPermissions": [
                {
                    "IpProtocol": "tcp",
                    "FromPort": 2049,
                    "ToPort": 2049,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                },
            ],
        },
    )

    efs_stubber.add_response(
        method="create_mount_target",
        service_response={
            "FileSystemId": fs_id,
            "IpAddress": "192.0.0.2",
            "LifeCycleState": "creating",
            "MountTargetId": mount_target_id,
            "NetworkInterfaceId": "eni-cedf6789",
            "OwnerId": owner_id,
            "SubnetId": subnet_id,
            "ResponseMetadata": {
                "...": "...",
            },
        },
        expected_params={
            "FileSystemId": fs_id,
            "SubnetId": subnet_id,
            "SecurityGroups": [sg_id],
        },
    )

    ssm_stubber.add_response(
        method="send_command",
        expected_params={
            "DocumentName": "AWS-RunShellScript",
            "Parameters": {"commands": mount_command, "executionTimeout": ["120"]},
            "InstanceIds": [instance_id],
        },
        service_response={
            "Command": {
                "CommandId": command_id,
            }
        },
    )

    mocked_get_session_credentials.return_value = (dummy_credentials, None)
    mocked_create_mount_targets.return_value = True
    mocked_wait_command.return_value = {"Status": "Failure"}
    mocked_get_efs_client.return_value = efs
    mocked_get_ec2_client.return_value = ec2
    mocked_get_ssm_client.return_value = ssm

    ec2_stubber.activate()
    efs_stubber.activate()
    ssm_stubber.activate()
    response = await efs_ops.mount_storage(
        credentials={"role_arn": role_arn, "region_name": region_name},
        instance_id=instance_id,
        path="/nfs/foo",
        storage_id=fs_id,
        public_subnet_id=subnet_id,
        private_subnet_id=subnet_id,
        vpc_id=vpc_id,
    )
    ec2_stubber.deactivate()
    efs_stubber.deactivate()
    ssm_stubber.deactivate()

    assert response is False
    mocked_create_mount_targets.assert_called_once_with(
        efs,
        fs_id,
        [subnet_id, subnet_id],
        sg_id,
    )
    mocked_wait_command.assert_called_once_with(
        ssm=ssm, command_id=command_id, instance_id=instance_id, time_out=120
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fs_id,fs_name,role_arn,region_name,owner_id,vpc_id,subnet_id",
    [
        (
            "fs-a1",
            "dummy-1",
            "arn:aws:iam::111111111111:role/test-1",
            "us-east-1",
            "111111111111",
            "vpc_id_a1",
            "subnet_id_aaaa1",
        ),
        (
            "fs-b2",
            "dummy-2",
            "arn:aws:iam::222222222222:role/test-2",
            "us-west-2",
            "222222222222",
            "vpc_id_b2",
            "subnet_id_bbbb2",
        ),
        (
            "fs-c3",
            "dummy-3",
            "arn:aws:iam::333333333333:role/test-3",
            "eu-north-1",
            "333333333333",
            "vpc_id_c3",
            "subnet_id_cccc3",
        ),
    ],
)
@mock.patch("api.efs_app.efs_ops.get_session_credentials")
@mock.patch("api.efs_app.efs_ops._get_efs_client")
@mock.patch("api.efs_app.efs_ops._get_ssm_client")
@mock.patch("api.efs_app.efs_ops.get_ec2_client")
@mock.patch("api.efs_app.efs_ops._create_mount_targets")
@mock.patch("api.efs_app.efs_ops._wait_command")
@mock.patch("api.efs_app.efs_ops.tag_instance")
async def test_mount_efs__check_storage_mounted_with_success(
    mocked_tag_instance: mock.MagicMock,
    mocked_wait_command: mock.Mock,
    mocked_create_mount_targets: mock.Mock,
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
    subnet_id: str,
):
    """Test if the mount file system is mounted with success."""
    sg_id = "sg-903004f8"
    mount_target_id = "fsmt-12340abc"
    instance_id = "instance_id"
    path = "/nfs/foo"
    command_id = "super_dummy_command_id_to_meet_the_length_requirement_36"
    dummy_credentials = {
        "aws_access_key_id": "test-access-key",
        "aws_secret_access_key": "test-secret-key",
        "aws_session_token": "test-session-token",
    }
    mount_command = [
        f"mkdir -p {path}",
        f"until nc -z -w 2 {fs_id}.efs.{region_name}.amazonaws.com 2049; do sleep 2; done;",
        f"sudo mount -t efs -o tls {fs_id}:/ {path}",
        f"sudo chown -R ubuntu:ubuntu {path}",
        f"echo 'storage {fs_id} mounted in {path}'",
    ]

    ec2 = botocore.session.get_session().create_client("ec2")
    efs = botocore.session.get_session().create_client("efs")
    ssm = botocore.session.get_session().create_client("ssm")
    ec2_stubber = Stubber(ec2)
    efs_stubber = Stubber(efs)
    ssm_stubber = Stubber(ssm)

    ec2_stubber.add_response(
        method="create_security_group",
        service_response={
            "GroupId": sg_id,
            "ResponseMetadata": {
                "...": "...",
            },
        },
        expected_params={
            "GroupName": fs_id,
            "VpcId": vpc_id,
            "Description": f"Security group to allow access to the {fs_id} EFS",
            "TagSpecifications": [
                {"ResourceType": "security-group", "Tags": [{"Key": "ManagedBy", "Value": "Vantage"}]}
            ],
        },
    )
    ec2_stubber.add_response(
        method="authorize_security_group_ingress",
        service_response={
            "Return": True,
            "SecurityGroupRules": [
                {
                    "SecurityGroupRuleId": "RuleId",
                    "GroupId": sg_id,
                    "IsEgress": False,
                    "FromPort": 2049,
                    "ToPort": 2049,
                }
            ],
        },
        expected_params={
            "GroupId": sg_id,
            "IpPermissions": [
                {
                    "IpProtocol": "tcp",
                    "FromPort": 2049,
                    "ToPort": 2049,
                    "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                },
            ],
        },
    )

    efs_stubber.add_response(
        method="create_mount_target",
        service_response={
            "FileSystemId": fs_id,
            "IpAddress": "192.0.0.2",
            "LifeCycleState": "creating",
            "MountTargetId": mount_target_id,
            "NetworkInterfaceId": "eni-cedf6789",
            "OwnerId": owner_id,
            "SubnetId": subnet_id,
            "ResponseMetadata": {
                "...": "...",
            },
        },
        expected_params={
            "FileSystemId": fs_id,
            "SubnetId": subnet_id,
            "SecurityGroups": [sg_id],
        },
    )

    ssm_stubber.add_response(
        method="send_command",
        expected_params={
            "DocumentName": "AWS-RunShellScript",
            "Parameters": {"commands": mount_command, "executionTimeout": ["120"]},
            "InstanceIds": [instance_id],
        },
        service_response={
            "Command": {
                "CommandId": command_id,
            }
        },
    )

    mocked_get_session_credentials.return_value = (dummy_credentials, None)
    mocked_create_mount_targets.return_value = True
    mocked_wait_command.return_value = {"Status": "Success"}
    mocked_get_efs_client.return_value = efs
    mocked_get_ec2_client.return_value = ec2
    mocked_get_ssm_client.return_value = ssm

    ec2_stubber.activate()
    efs_stubber.activate()
    ssm_stubber.activate()
    response = await efs_ops.mount_storage(
        credentials={"role_arn": role_arn, "region_name": region_name},
        instance_id=instance_id,
        path="/nfs/foo",
        storage_id=fs_id,
        public_subnet_id=subnet_id,
        private_subnet_id=subnet_id,
        vpc_id=vpc_id,
    )
    ec2_stubber.deactivate()
    efs_stubber.deactivate()
    ssm_stubber.deactivate()

    assert response is True
    mocked_create_mount_targets.assert_called_once_with(
        efs,
        fs_id,
        [subnet_id, subnet_id],
        sg_id,
    )
    mocked_wait_command.assert_called_once_with(
        ssm=ssm, command_id=command_id, instance_id=instance_id, time_out=120
    )
    mocked_tag_instance.assert_called_once_with(
        instance_id=instance_id,
        tags={f"mount-target/{fs_id}": "/nfs/foo"},
        credentials=dummy_credentials,
    )
