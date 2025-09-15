"""Core module for testing the STS operations module."""
from unittest import TestCase, mock

import pytest
from pytest_mock import MockFixture

from api.settings import SETTINGS
from api.sts_app.sts_ops import get_session_credentials, get_sts_client


@pytest.mark.asyncio
async def test_sts_ops__get_session_credentials_with_success(mocker: MockFixture):
    """Test when get_session_credentials function is called and returns without errors."""
    role_arn = "dummy_role_arn"
    region_name = "us-west-2"
    unformatted_credentials = {
        "AccessKeyId": "dummy_access_key_id",
        "SecretAccessKey": "dummy_secret",
        "SessionToken": "dummy_token",
    }
    formatted_credentials = {
        "aws_access_key_id": "dummy_access_key_id",
        "aws_secret_access_key": "dummy_secret",
        "aws_session_token": "dummy_token",
        "region_name": region_name,
    }

    sts_mock = mock.Mock()
    sts_mock.assume_role = mock.Mock(return_value={"Credentials": unformatted_credentials})
    mock_get_sts_client = mock.Mock(return_value=(sts_mock))
    mocker.patch("api.cfn_app.cfn_ops.sts_ops.get_sts_client", mock_get_sts_client)

    response_credentials, response_sts = get_session_credentials(role_arn, region_name)

    assert response_sts is sts_mock
    TestCase().assertDictEqual(formatted_credentials, response_credentials)
    mock_get_sts_client.assert_has_calls(
        calls=[mock.call(use_custom_endpoint=True), mock.call(formatted_credentials)]
    )


@pytest.mark.asyncio
@mock.patch("api.sts_app.sts_ops.boto3")
async def test_cfn_ops__get_boto3_sts_client(mocked_boto3: mock.MagicMock):
    """Test function to get boto3 client with the sts service."""
    mocked_boto3.client = mock.Mock(return_value="dummy_sts_client")

    credentials = {
        "aws_access_key_id": "123123",
        "aws_secret_access_key": "123123",
        "region_name": "region",
        "aws_session_token": "123456",
    }

    response = get_sts_client(credentials)

    assert response == "dummy_sts_client"
    mocked_boto3.client.assert_called_once_with("sts", **credentials, endpoint_url=SETTINGS.AWS_ENDPOINT_URL)
