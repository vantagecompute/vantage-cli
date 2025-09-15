"""Core module for testing the mktplace_ops module."""
from unittest import mock

import pytest

from api.metering_mktplace_app.metering_mktplace_ops import _assume_mkt_role, get_metering_mkt_client
from api.settings import SETTINGS


@mock.patch("api.metering_mktplace_app.metering_mktplace_ops.get_session_credentials")
@pytest.mark.parametrize(
    "access_key_id, secret_access_key, session_token, region_name",
    [
        ("test1", "test2", "test3", "us-east-1"),
        ("test4", "test5", "test6", "us-west-1"),
    ],
)
def test__assume_mkt_role__default_role_name_mkt(
    mocked_get_session_credentials: mock.MagicMock,
    access_key_id: str,
    secret_access_key: str,
    session_token: str,
    region_name: str,
):
    """Test the _assume_mkt_role function."""
    expected_credentials = {
        "aws_access_key_id": access_key_id,
        "aws_secret_access_key": secret_access_key,
        "aws_session_token": session_token,
        "region_name": region_name,
    }

    mocked_get_session_credentials.return_value = (expected_credentials, None)

    actual_creds = _assume_mkt_role()

    mocked_get_session_credentials.assert_called_once_with(
        SETTINGS.AWS_ROLE_NAME_MKT, region_name="us-east-1", use_custom_endpoint=False
    )
    assert actual_creds == expected_credentials


@mock.patch("api.metering_mktplace_app.metering_mktplace_ops.get_session_credentials")
@pytest.mark.parametrize(
    "access_key_id, secret_access_key, session_token, region_name, role_name",
    [
        ("test1", "test2", "test3", "us-east-1", "test4"),
        ("test5", "test6", "test7", "us-west-1", "test8"),
    ],
)
def test__assume_mkt_role__patch_role_to_assume(
    mocked_get_session_credentials: mock.MagicMock,
    access_key_id: str,
    secret_access_key: str,
    session_token: str,
    region_name: str,
    role_name: str,
):
    """Test the _assume_mkt_role function."""
    expected_credentials = {
        "aws_access_key_id": access_key_id,
        "aws_secret_access_key": secret_access_key,
        "aws_session_token": session_token,
        "region_name": region_name,
    }

    mocked_get_session_credentials.return_value = (expected_credentials, None)

    with mock.patch("api.metering_mktplace_app.metering_mktplace_ops.SETTINGS.AWS_ROLE_NAME_MKT", role_name):
        actual_creds = _assume_mkt_role()

    mocked_get_session_credentials.assert_called_once_with(
        role_name, region_name="us-east-1", use_custom_endpoint=False
    )
    assert actual_creds == expected_credentials


@mock.patch("api.metering_mktplace_app.metering_mktplace_ops.boto3.client")
@mock.patch("api.metering_mktplace_app.metering_mktplace_ops._assume_mkt_role")
def test_get_metering_mkt_client(
    mocked__assume_mkt_role: mock.MagicMock, mocked_boto3_client: mock.MagicMock
):
    """Test the get_metering_mkt_client function."""
    expected_client = mock.MagicMock()
    mocked_boto3_client.return_value = expected_client

    mocked__assume_mkt_role.return_value = {
        "aws_access_key_id": "test1",
        "aws_secret_access_key": "test2",
        "aws_session_token": "test3",
        "region_name": "us-east-1",
    }

    actual_client = get_metering_mkt_client()

    assert actual_client == expected_client
    mocked_boto3_client.assert_called_once_with("meteringmarketplace", **mocked__assume_mkt_role.return_value)
