"""Test the AWS EFS operations."""
import datetime
from typing import Dict
from unittest import mock

import botocore.session
import pytest
from botocore.stub import Stubber

from api.efs_app import efs_ops
from api.settings import SETTINGS


@pytest.mark.parametrize(
    "fs_id,role_arn,region_name,owner_id",
    [
        ("fs-a1", "arn:aws:iam::111111111111:role/test-1", "us-east-1", "111111111111"),
        ("fs-b2", "arn:aws:iam::222222222222:role/test-2", "us-west-2", "222222222222"),
        ("fs-c3", "arn:aws:iam::333333333333:role/test-3", "eu-north-1", "333333333333"),
    ],
)
@mock.patch("api.efs_app.efs_ops.get_session_credentials")
@mock.patch("api.efs_app.efs_ops._get_efs_client")
def test_delete_efs__check_successful_deletion(
    mocked_get_efs_client: mock.Mock,
    mocked_get_session_credentials: mock.Mock,
    fs_id: str,
    role_arn: str,
    region_name: str,
    owner_id: str,
):
    """Check if the file system can be deleted successfully."""
    efs = botocore.session.get_session().create_client("efs")
    stubber = Stubber(efs)

    describe_file_systems_response = {
        "ResponseMetadata": {
            "RequestId": "08facc62-64cb-4171-b688-bc3b71a5ef37",
            "HTTPStatusCode": 200,
            "HTTPHeaders": {
                "x-amzn-requestid": "08facc62-64cb-4171-b688-bc3b71a5ef37",
                "content-type": "application/json",
                "content-length": "845",
                "date": "Thu, 20 Jul 2023 14:37:48 GMT",
            },
            "RetryAttempts": 0,
        },
        "FileSystems": [
            {
                "OwnerId": owner_id,
                "CreationToken": "quickCreated-dd857072-e9eb-4a26-b760-ac0238d1183e",
                "FileSystemId": fs_id,
                "FileSystemArn": f"arn:aws:elasticfilesystem:{region_name}:{owner_id}:file-system/{fs_id}",
                "CreationTime": datetime.datetime(2023, 7, 20, 10, 37, 23),
                "LifeCycleState": "available",
                "Name": "test",
                "NumberOfMountTargets": 4,
                "SizeInBytes": {"Value": 6144, "ValueInIA": 0, "ValueInStandard": 6144},
                "PerformanceMode": "generalPurpose",
                "Encrypted": True,
                "KmsKeyId": "arn:aws:kms:us-west-2:266735843730:key/26b488b5-3e5d-460d-aa02-5b1970965e0b",
                "ThroughputMode": "elastic",
                "Tags": [
                    {"Key": "Name", "Value": "test"},
                    {"Key": "aws:elasticfilesystem:default-backup", "Value": "enabled"},
                    {"Key": "ManagedBy", "Value": "Vantage"},
                ],
            }
        ],
    }

    mount_targets = [
        {
            "OwnerId": owner_id,
            "MountTargetId": "fsmt-00af1e455a9740be4",
            "FileSystemId": fs_id,
            "SubnetId": "subnet-b829efe5",
            "LifeCycleState": "available",
            "IpAddress": "172.31.8.39",
            "NetworkInterfaceId": "eni-004aeea52dec081c8",
            "AvailabilityZoneName": f"{region_name}c",
            "VpcId": "vpc-9653c9ee",
        },
        {
            "OwnerId": owner_id,
            "MountTargetId": "fsmt-01d926b7d34bece0c",
            "FileSystemId": fs_id,
            "SubnetId": "subnet-96fa84bd",
            "LifeCycleState": "available",
            "IpAddress": "172.31.48.236",
            "NetworkInterfaceId": "eni-0be1b0a5da9b1db18",
            "AvailabilityZoneName": f"{region_name}d",
            "VpcId": "vpc-9653c9ee",
        },
        {
            "OwnerId": owner_id,
            "MountTargetId": "fsmt-0796e6b17a15a70f7",
            "FileSystemId": fs_id,
            "SubnetId": "subnet-86a0b1cd",
            "LifeCycleState": "available",
            "IpAddress": "172.31.47.192",
            "NetworkInterfaceId": "eni-01bcb7960717d7529",
            "AvailabilityZoneName": f"{region_name}b",
            "VpcId": "vpc-9653c9ee",
        },
        {
            "OwnerId": owner_id,
            "MountTargetId": "fsmt-0d73038aa4b348df5",
            "FileSystemId": fs_id,
            "SubnetId": "subnet-6af30412",
            "LifeCycleState": "available",
            "IpAddress": "172.31.19.40",
            "NetworkInterfaceId": "eni-08cf538659314fbc5",
            "AvailabilityZoneName": f"{region_name}a",
            "VpcId": "vpc-9653c9ee",
        },
    ]

    describe_mount_targets_response = {
        "ResponseMetadata": {
            "RequestId": "982c6714-e405-4ebc-b5ac-67b06575487c",
            "HTTPStatusCode": 200,
            "HTTPHeaders": {
                "x-amzn-requestid": "982c6714-e405-4ebc-b5ac-67b06575487c",
                "content-type": "application/json",
                "content-length": "1359",
                "date": "Thu, 20 Jul 2023 14:59:17 GMT",
            },
            "RetryAttempts": 0,
        },
        "MountTargets": mount_targets,
    }

    delete_mount_target_response = {
        "ResponseMetadata": {
            "RequestId": "959f18c0-af0b-4cab-88ff-aaece1a42519",
            "HTTPStatusCode": 204,
            "HTTPHeaders": {
                "x-amzn-requestid": "959f18c0-af0b-4cab-88ff-aaece1a42519",
                "content-type": "application/json",
                "date": "Thu, 20 Jul 2023 15:32:48 GMT",
            },
            "RetryAttempts": 0,
        }
    }

    delete_file_system_response = {
        "ResponseMetadata": {
            "RequestId": "e56050b9-0ced-40f4-8b4c-1c3b2c1b77c6",
            "HTTPStatusCode": 204,
            "HTTPHeaders": {
                "x-amzn-requestid": "e56050b9-0ced-40f4-8b4c-1c3b2c1b77c6",
                "content-type": "application/json",
                "date": "Thu, 20 Jul 2023 15:37:53 GMT",
            },
            "RetryAttempts": 0,
        }
    }

    stubber.add_response("describe_file_systems", describe_file_systems_response, {"FileSystemId": fs_id})
    stubber.add_response("describe_mount_targets", describe_mount_targets_response, {"FileSystemId": fs_id})
    for mount_target in mount_targets:
        stubber.add_response(
            "delete_mount_target",
            delete_mount_target_response,
            {"MountTargetId": mount_target["MountTargetId"]},
        )
    stubber.add_response("delete_file_system", delete_file_system_response, {"FileSystemId": fs_id})

    dummy_credentials = {
        "aws_access_key_id": "test-access-key",
        "aws_secret_access_key": "test-secret-key",
        "aws_session_token": "test-session-token",
    }

    mocked_get_session_credentials.return_value = (dummy_credentials, None)
    mocked_get_efs_client.return_value = efs

    stubber.activate()
    response = efs_ops.delete_efs(fs_id, role_arn, region_name)
    stubber.deactivate()

    assert response is True
    mocked_get_efs_client.assert_called_once_with(dummy_credentials)
    mocked_get_session_credentials.assert_called_once_with(role_arn, region_name)


@pytest.mark.parametrize(
    "fs_id,role_arn,region_name,owner_id",
    [
        ("fs-a1", "arn:aws:iam::111111111111:role/test-1", "us-east-1", "111111111111"),
        ("fs-b2", "arn:aws:iam::222222222222:role/test-2", "us-west-2", "222222222222"),
        ("fs-c3", "arn:aws:iam::333333333333:role/test-3", "eu-north-1", "333333333333"),
    ],
)
@mock.patch("api.efs_app.efs_ops.get_session_credentials")
@mock.patch("api.efs_app.efs_ops._get_efs_client")
def test_delete_efs__check_when_file_system_isnt_tagged_correctly__no_managedby_tag(
    mocked_get_efs_client: mock.Mock,
    mocked_get_session_credentials: mock.Mock,
    fs_id: str,
    role_arn: str,
    region_name: str,
    owner_id: str,
):
    """Check when the file system isn't tagged with the ManagedBy tag."""
    efs = botocore.session.get_session().create_client("efs")
    stubber = Stubber(efs)

    describe_file_systems_response = {
        "ResponseMetadata": {
            "RequestId": "08facc62-64cb-4171-b688-bc3b71a5ef37",
            "HTTPStatusCode": 200,
            "HTTPHeaders": {
                "x-amzn-requestid": "08facc62-64cb-4171-b688-bc3b71a5ef37",
                "content-type": "application/json",
                "content-length": "845",
                "date": "Thu, 20 Jul 2023 14:37:48 GMT",
            },
            "RetryAttempts": 0,
        },
        "FileSystems": [
            {
                "OwnerId": owner_id,
                "CreationToken": "quickCreated-dd857072-e9eb-4a26-b760-ac0238d1183e",
                "FileSystemId": fs_id,
                "FileSystemArn": f"arn:aws:elasticfilesystem:{region_name}:{owner_id}:file-system/{fs_id}",
                "CreationTime": datetime.datetime(2023, 7, 20, 10, 37, 23),
                "LifeCycleState": "available",
                "Name": "test",
                "NumberOfMountTargets": 4,
                "SizeInBytes": {"Value": 6144, "ValueInIA": 0, "ValueInStandard": 6144},
                "PerformanceMode": "generalPurpose",
                "Encrypted": True,
                "KmsKeyId": "arn:aws:kms:us-west-2:266735843730:key/26b488b5-3e5d-460d-aa02-5b1970965e0b",
                "ThroughputMode": "elastic",
                "Tags": [
                    # it doesn't have the ManagedBy tag
                    {"Key": "Name", "Value": "test"},
                    {"Key": "aws:elasticfilesystem:default-backup", "Value": "enabled"},
                ],
            }
        ],
    }

    stubber.add_response("describe_file_systems", describe_file_systems_response, {"FileSystemId": fs_id})

    dummy_credentials = {
        "aws_access_key_id": "test-access-key",
        "aws_secret_access_key": "test-secret-key",
        "aws_session_token": "test-session-token",
    }

    mocked_get_session_credentials.return_value = (dummy_credentials, None)
    mocked_get_efs_client.return_value = efs

    stubber.activate()
    response = efs_ops.delete_efs(fs_id, role_arn, region_name)
    stubber.deactivate()

    assert response is False
    mocked_get_efs_client.assert_called_once_with(dummy_credentials)
    mocked_get_session_credentials.assert_called_once_with(role_arn, region_name)


@pytest.mark.parametrize(
    "fs_id,role_arn,region_name",
    [
        ("fs-a1", "arn:aws:iam::111111111111:role/test-1", "us-east-1"),
        ("fs-b2", "arn:aws:iam::222222222222:role/test-2", "us-west-2"),
        ("fs-c3", "arn:aws:iam::333333333333:role/test-3", "eu-north-1"),
    ],
)
@mock.patch("api.efs_app.efs_ops.get_session_credentials")
@mock.patch("api.efs_app.efs_ops._get_efs_client")
def test_delete_efs__check_when_file_system_not_found(
    mocked_get_efs_client: mock.Mock,
    mocked_get_session_credentials: mock.Mock,
    fs_id: str,
    role_arn: str,
    region_name: str,
):
    """Check when the file system doesn't exist."""
    efs = botocore.session.get_session().create_client("efs")
    stubber = Stubber(efs)
    stubber.add_client_error(
        "describe_file_systems",
        "FileSystemNotFound",
        f"File system '{fs_id}' does not exist.",
        404,
        expected_params={"FileSystemId": fs_id},
    )

    dummy_credentials = {
        "aws_access_key_id": "test-access-key",
        "aws_secret_access_key": "test-secret-key",
        "aws_session_token": "test-session-token",
    }

    mocked_get_session_credentials.return_value = (dummy_credentials, None)
    mocked_get_efs_client.return_value = efs

    stubber.activate()
    response = efs_ops.delete_efs(fs_id, role_arn, region_name)
    stubber.deactivate()

    assert response is False
    mocked_get_efs_client.assert_called_once_with(dummy_credentials)
    mocked_get_session_credentials.assert_called_once_with(role_arn, region_name)


@pytest.mark.parametrize(
    "fs_id,role_arn,region_name,owner_id",
    [
        ("fs-a1", "arn:aws:iam::111111111111:role/test-1", "us-east-1", "111111111111"),
        ("fs-b2", "arn:aws:iam::222222222222:role/test-2", "us-west-2", "222222222222"),
        ("fs-c3", "arn:aws:iam::333333333333:role/test-3", "eu-north-1", "333333333333"),
    ],
)
@mock.patch("api.efs_app.efs_ops.get_session_credentials")
@mock.patch("api.efs_app.efs_ops._get_efs_client")
def test_delete_efs__check_when_file_system_isnt_tagged_correctly__managedby_tag_with_different_value(
    mocked_get_efs_client: mock.Mock,
    mocked_get_session_credentials: mock.Mock,
    fs_id: str,
    role_arn: str,
    region_name: str,
    owner_id: str,
):
    """Check when the file system is tagged with the ManagedBy tag but with not expected value."""
    efs = botocore.session.get_session().create_client("efs")
    stubber = Stubber(efs)

    describe_file_systems_response = {
        "ResponseMetadata": {
            "RequestId": "08facc62-64cb-4171-b688-bc3b71a5ef37",
            "HTTPStatusCode": 200,
            "HTTPHeaders": {
                "x-amzn-requestid": "08facc62-64cb-4171-b688-bc3b71a5ef37",
                "content-type": "application/json",
                "content-length": "845",
                "date": "Thu, 20 Jul 2023 14:37:48 GMT",
            },
            "RetryAttempts": 0,
        },
        "FileSystems": [
            {
                "OwnerId": owner_id,
                "CreationToken": "quickCreated-dd857072-e9eb-4a26-b760-ac0238d1183e",
                "FileSystemId": fs_id,
                "FileSystemArn": f"arn:aws:elasticfilesystem:{region_name}:{owner_id}:file-system/{fs_id}",
                "CreationTime": datetime.datetime(2023, 7, 20, 10, 37, 23),
                "LifeCycleState": "available",
                "Name": "test",
                "NumberOfMountTargets": 4,
                "SizeInBytes": {"Value": 6144, "ValueInIA": 0, "ValueInStandard": 6144},
                "PerformanceMode": "generalPurpose",
                "Encrypted": True,
                "KmsKeyId": "arn:aws:kms:us-west-2:266735843730:key/26b488b5-3e5d-460d-aa02-5b1970965e0b",
                "ThroughputMode": "elastic",
                "Tags": [
                    {"Key": "Name", "Value": "test"},
                    {"Key": "aws:elasticfilesystem:default-backup", "Value": "enabled"},
                    {"Key": "ManagedBy", "Value": "Dummy"},
                ],
            }
        ],
    }

    stubber.add_response("describe_file_systems", describe_file_systems_response, {"FileSystemId": fs_id})

    dummy_credentials = {
        "aws_access_key_id": "test-access-key",
        "aws_secret_access_key": "test-secret-key",
        "aws_session_token": "test-session-token",
    }

    mocked_get_session_credentials.return_value = (dummy_credentials, None)
    mocked_get_efs_client.return_value = efs

    stubber.activate()
    response = efs_ops.delete_efs(fs_id, role_arn, region_name)
    stubber.deactivate()

    assert response is False
    mocked_get_efs_client.assert_called_once_with(dummy_credentials)
    mocked_get_session_credentials.assert_called_once_with(role_arn, region_name)


@pytest.mark.parametrize(
    "dummy_return,credentials",
    [
        (
            "1",
            {
                "aws_access_key_id": "test-access-key",
                "aws_secret_access_key": "test-secret-key",
                "aws_session_token": "test-session-token",
            },
        ),
        (
            "abc",
            {
                "aws_access_key_id": "dummy-access-key",
                "aws_secret_access_key": "dummy-secret-key",
                "aws_session_token": "dummy-session-token",
            },
        ),
    ],
)
@mock.patch("api.efs_app.efs_ops.boto3")
def test_get_efs_client(mocked_boto3: mock.Mock, dummy_return: str, credentials: Dict[str, str]):
    """Check if the EFS client is instantiated as expected."""
    mocked_boto3.client.return_value = dummy_return

    response = efs_ops._get_efs_client(credentials)

    assert response == dummy_return
    mocked_boto3.client.assert_called_once_with("efs", **credentials, endpoint_url=SETTINGS.AWS_ENDPOINT_URL)


@pytest.mark.parametrize(
    "fs_id,fs_name,role_arn,region_name,owner_id",
    [
        ("fs-a1", "dummy-1", "arn:aws:iam::111111111111:role/test-1", "us-east-1", "111111111111"),
        ("fs-b2", "dummy-2", "arn:aws:iam::222222222222:role/test-2", "us-west-2", "222222222222"),
        ("fs-c3", "dummy-3", "arn:aws:iam::333333333333:role/test-3", "eu-north-1", "333333333333"),
    ],
)
@mock.patch("api.efs_app.efs_ops.get_session_credentials")
@mock.patch("api.efs_app.efs_ops._get_efs_client")
def test_create_efs__check_successful_creation(
    mocked_get_efs_client: mock.Mock,
    mocked_get_session_credentials: mock.Mock,
    fs_id: str,
    fs_name: str,
    role_arn: str,
    region_name: str,
    owner_id: str,
):
    """Test if the file system is created successfully."""
    efs = botocore.session.get_session().create_client("efs")
    stubber = Stubber(efs)

    describe_file_systems_response = {
        "ResponseMetadata": {
            "RequestId": "08facc62-64cb-4171-b688-bc3b71a5ef37",
            "HTTPStatusCode": 200,
            "HTTPHeaders": {
                "x-amzn-requestid": "08facc62-64cb-4171-b688-bc3b71a5ef37",
                "content-type": "application/json",
                "content-length": "845",
                "date": "Thu, 20 Jul 2023 14:37:48 GMT",
            },
            "RetryAttempts": 0,
        },
        "FileSystems": [],
    }

    create_file_system_response = {
        "ResponseMetadata": {
            "RequestId": "c65e51ff-64fc-4f14-b693-afd405247118",
            "HTTPStatusCode": 201,
            "HTTPHeaders": {
                "x-amzn-requestid": "c65e51ff-64fc-4f14-b693-afd405247118",
                "content-type": "application/json",
                "content-length": "643",
                "date": "Thu, 20 Jul 2023 18:15:20 GMT",
            },
            "RetryAttempts": 0,
        },
        "OwnerId": owner_id,
        "CreationToken": fs_name,
        "FileSystemId": fs_id,
        "FileSystemArn": f"arn:aws:elasticfilesystem:{region_name}:{owner_id}:file-system/{fs_id}",
        "CreationTime": datetime.datetime(2023, 7, 20, 14, 15, 20),
        "LifeCycleState": "creating",
        "Name": fs_name,
        "NumberOfMountTargets": 0,
        "SizeInBytes": {"Value": 0, "ValueInIA": 0, "ValueInStandard": 0},
        "PerformanceMode": "generalPurpose",
        "Encrypted": False,
        "ThroughputMode": "elastic",
        "Tags": [{"Key": "ManagedBy", "Value": "Vantage"}, {"Key": "Name", "Value": fs_name}],
    }

    stubber.add_response("describe_file_systems", describe_file_systems_response, {"CreationToken": fs_name})
    stubber.add_response(
        "create_file_system",
        create_file_system_response,
        {
            "ThroughputMode": "elastic",
            "PerformanceMode": "generalPurpose",
            "Tags": [{"Key": "ManagedBy", "Value": "Vantage"}, {"Key": "Name", "Value": fs_name}],
            "CreationToken": fs_name,
        },
    )

    dummy_credentials = {
        "aws_access_key_id": "test-access-key",
        "aws_secret_access_key": "test-secret-key",
        "aws_session_token": "test-session-token",
    }

    mocked_get_session_credentials.return_value = (dummy_credentials, None)
    mocked_get_efs_client.return_value = efs

    stubber.activate()
    response = efs_ops.create_efs(fs_name, role_arn, region_name)
    stubber.deactivate()

    assert response == fs_id
    mocked_get_efs_client.assert_called_once_with(dummy_credentials)
    mocked_get_session_credentials.assert_called_once_with(role_arn, region_name)


@pytest.mark.parametrize(
    "fs_id,fs_name,role_arn,region_name,owner_id",
    [
        ("fs-a1", "dummy-1", "arn:aws:iam::111111111111:role/test-1", "us-east-1", "111111111111"),
        ("fs-b2", "dummy-2", "arn:aws:iam::222222222222:role/test-2", "us-west-2", "222222222222"),
        ("fs-c3", "dummy-3", "arn:aws:iam::333333333333:role/test-3", "eu-north-1", "333333333333"),
    ],
)
@mock.patch("api.efs_app.efs_ops.get_session_credentials")
@mock.patch("api.efs_app.efs_ops._get_efs_client")
def test_create_efs__check_failure_when_fs_name_in_use(
    mocked_get_efs_client: mock.Mock,
    mocked_get_session_credentials: mock.Mock,
    fs_id: str,
    fs_name: str,
    role_arn: str,
    region_name: str,
    owner_id: str,
):
    """Test if the file system creation fails when the file system name is in use."""
    efs = botocore.session.get_session().create_client("efs")
    stubber = Stubber(efs)

    describe_file_systems_response = {
        "ResponseMetadata": {
            "RequestId": "08facc62-64cb-4171-b688-bc3b71a5ef37",
            "HTTPStatusCode": 200,
            "HTTPHeaders": {
                "x-amzn-requestid": "08facc62-64cb-4171-b688-bc3b71a5ef37",
                "content-type": "application/json",
                "content-length": "845",
                "date": "Thu, 20 Jul 2023 14:37:48 GMT",
            },
            "RetryAttempts": 0,
        },
        "FileSystems": [
            {
                "OwnerId": owner_id,
                "CreationToken": "quickCreated-dd857072-e9eb-4a26-b760-ac0238d1183e",
                "FileSystemId": fs_id,
                "FileSystemArn": f"arn:aws:elasticfilesystem:{region_name}:{owner_id}:file-system/{fs_id}",
                "CreationTime": datetime.datetime(2023, 7, 20, 10, 37, 23),
                "LifeCycleState": "available",
                "Name": "test",
                "NumberOfMountTargets": 4,
                "SizeInBytes": {"Value": 6144, "ValueInIA": 0, "ValueInStandard": 6144},
                "PerformanceMode": "generalPurpose",
                "Encrypted": True,
                "KmsKeyId": "arn:aws:kms:us-west-2:266735843730:key/26b488b5-3e5d-460d-aa02-5b1970965e0b",
                "ThroughputMode": "elastic",
                "Tags": [
                    {"Key": "Name", "Value": "test"},
                    {"Key": "aws:elasticfilesystem:default-backup", "Value": "enabled"},
                    {"Key": "ManagedBy", "Value": "Vantage"},
                ],
            }
        ],
    }

    stubber.add_response("describe_file_systems", describe_file_systems_response, {"CreationToken": fs_name})

    dummy_credentials = {
        "aws_access_key_id": "test-access-key",
        "aws_secret_access_key": "test-secret-key",
        "aws_session_token": "test-session-token",
    }

    mocked_get_session_credentials.return_value = (dummy_credentials, None)
    mocked_get_efs_client.return_value = efs

    stubber.activate()
    response = efs_ops.create_efs(fs_name, role_arn, region_name)
    stubber.deactivate()

    assert response is None
    mocked_get_efs_client.assert_called_once_with(dummy_credentials)
    mocked_get_session_credentials.assert_called_once_with(role_arn, region_name)
