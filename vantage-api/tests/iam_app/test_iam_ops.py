"""Core module for testing the IAM operations module."""
import json
from unittest import mock

import boto3
import botocore.exceptions
import httpx
import pytest
import respx
from botocore.stub import Stubber

from api.iam_app.iam_ops import (
    AssumedSessionCredentials,
    check_iam_role_state,
    fetch_upstream_policy_document,
    get_iam_client,
)
from api.settings import SETTINGS


@pytest.mark.asyncio
@mock.patch("api.iam_app.iam_ops.boto3")
async def test_iam_ops__get_boto3_iam_client(mocked_boto3: mock.MagicMock):
    """Test function to get boto3 client with the IAM service."""
    mocked_boto3.client = mock.Mock(return_value="dummy_iam_client")

    credentials: AssumedSessionCredentials = {
        "aws_access_key_id": "123123",
        "aws_secret_access_key": "123123",
        "region_name": "region",
        "aws_session_token": "123456",
    }

    response = get_iam_client(credentials)

    assert response == "dummy_iam_client"
    mocked_boto3.client.assert_called_once_with("iam", **credentials, endpoint_url=SETTINGS.AWS_ENDPOINT_URL)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "upstream_policy_url, policy_document",
    [
        ("https://example.org/vantage.json", {"Version": "2012-10-17", "Statement": []}),
        (
            "https://dummy.com/policy.json",
            {
                "Version": "2012-10-17",
                "Statement": [
                    {"Effect": "Allow", "Action": "s3:GetObject", "Resource": "arn:aws:s3:::example-bucket/*"}
                ],
            },
        ),
    ],
)
async def test_fetch_upstream_policy_document__no_http_error(
    upstream_policy_url: str, policy_document: dict[str, str | list[dict[str, str]]]
):
    """Test function to fetch the upstream policy document."""
    with respx.mock, mock.patch.object(SETTINGS, "VANTAGE_INTEGRATION_POLICY_URL", upstream_policy_url):
        respx.get(upstream_policy_url).mock(return_value=httpx.Response(200, json=policy_document))

        response = await fetch_upstream_policy_document()

    assert response == policy_document


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "upstream_policy_url, http_code",
    [
        ("https://example.org/vantage.json", 404),
        ("https://dummy.com/policy.json", 500),
    ],
)
async def test_fetch_upstream_policy_document__http_error(upstream_policy_url: str, http_code: int):
    """Test function to fetch the upstream policy document when there's an HTTP error."""
    with respx.mock, mock.patch.object(
        SETTINGS, "VANTAGE_INTEGRATION_POLICY_URL", upstream_policy_url
    ), pytest.raises(httpx.HTTPStatusError):
        respx.get(upstream_policy_url).mock(return_value=httpx.Response(http_code))
        await fetch_upstream_policy_document()


@pytest.mark.asyncio
@mock.patch("api.iam_app.iam_ops.get_session_credentials")
async def test_check_iam_role_state__role_not_found_or_not_accessible_when_assuming_role(
    mocked_get_session_credentials: mock.MagicMock,
):
    """Test function to check the state of the IAM role when missing permissions."""
    role_arn = "arn:aws:iam::123456789012:role/role_name"

    mocked_get_session_credentials.side_effect = botocore.exceptions.ClientError(
        {"Error": {"Code": "AccessDenied"}}, "get_session_credentials"
    )

    response = await check_iam_role_state(role_arn)

    assert response == "NOT_FOUND_OR_NOT_ACCESSIBLE"
    mocked_get_session_credentials.assert_called_once_with(role_arn, "us-east-1")


@pytest.mark.asyncio
@mock.patch("api.iam_app.iam_ops.get_session_credentials")
@mock.patch("api.iam_app.iam_ops.fetch_upstream_policy_document")
@mock.patch("api.iam_app.iam_ops.get_iam_client")
async def test_check_iam_role_state__missing_permissions_when_comparing_to_upstream(
    mocked_get_iam_client: mock.MagicMock,
    mocked_fetch_upstream_policy_document: mock.MagicMock,
    mocked_get_session_credentials: mock.MagicMock,
):
    """Test function to check the state of the IAM role when missing permissions compared to the upstream policy."""  # noqa: E501
    role_arn = "arn:aws:iam::123456789012:role/role_name"
    credentials: AssumedSessionCredentials = {
        "aws_access_key_id": "123123",
        "aws_secret_access_key": "123123",
        "region_name": "region",
        "aws_session_token": "123456",
    }
    upstream_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": [
                    "cloudformation:CreateStack",
                    "cloudformation:DeleteStack",
                    "cloudformation:DescribeStackEvents",
                    "cloudformation:UntagResource",
                    "cloudformation:UpdateStack",
                ],
                "Resource": "*",
                "Effect": "Allow",
                "Sid": "AllowCreateStacks",
            }
        ],
    }
    actual_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": [
                    "cloudformation:DescribeStackResources",
                    "cloudformation:SetStackPolicy",
                    "cloudformation:TagResource",
                    "cloudformation:UpdateStack",
                ],
                "Resource": "*",
                "Effect": "Allow",
                "Sid": "AllowCreateStacks",
            },
            {
                "Action": [
                    "cloudformation:CreateStack",
                    "cloudformation:DeleteStack",
                ],
                "Resource": "*",
                "Effect": "Allow",
                "Sid": "AllowCreateStacks",
            },
        ],
    }
    iam_client = boto3.client("iam")

    mocked_get_session_credentials.return_value = (credentials, None)

    mocked_get_iam_client.return_value = iam_client

    mocked_fetch_upstream_policy_document.return_value = upstream_policy_document

    stubber = Stubber(iam_client)
    stubber.add_response("list_role_policies", {"PolicyNames": ["policy1"]}, {"RoleName": "role_name"})
    stubber.add_response(
        "get_role_policy",
        {
            "RoleName": "role_name",
            "PolicyName": "policy1",
            "PolicyDocument": json.dumps(actual_policy_document),
        },
        {"RoleName": "role_name", "PolicyName": "policy1"},
    )

    with stubber:
        response = await check_iam_role_state(role_arn)

    assert response == "MISSING_PERMISSIONS"
    mocked_get_session_credentials.assert_called_once_with(role_arn, "us-east-1")
    mocked_get_session_credentials.assert_called_once_with(role_arn, "us-east-1")
    mocked_get_iam_client.assert_called_once_with(credentials)


@pytest.mark.asyncio
@mock.patch("api.iam_app.iam_ops.get_session_credentials")
@mock.patch("api.iam_app.iam_ops.fetch_upstream_policy_document")
@mock.patch("api.iam_app.iam_ops.get_iam_client")
async def test_check_iam_role_state__valid_role(
    mocked_get_iam_client: mock.MagicMock,
    mocked_fetch_upstream_policy_document: mock.MagicMock,
    mocked_get_session_credentials: mock.MagicMock,
):
    """Test function to check the state of the IAM role when it is valid."""
    role_arn = "arn:aws:iam::123456789012:role/role_name"
    credentials: AssumedSessionCredentials = {
        "aws_access_key_id": "123123",
        "aws_secret_access_key": "123123",
        "region_name": "region",
        "aws_session_token": "123456",
    }
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": [
                    "cloudformation:CreateStack",
                    "cloudformation:DeleteStack",
                    "cloudformation:DescribeStackEvents",
                    "cloudformation:UntagResource",
                    "cloudformation:UpdateStack",
                ],
                "Resource": "*",
                "Effect": "Allow",
                "Sid": "AllowCreateStacks",
            }
        ],
    }
    iam_client = boto3.client("iam")

    mocked_get_session_credentials.return_value = (credentials, None)

    mocked_get_iam_client.return_value = iam_client

    mocked_fetch_upstream_policy_document.return_value = policy_document

    stubber = Stubber(iam_client)
    stubber.add_response("list_role_policies", {"PolicyNames": ["policy1"]}, {"RoleName": "role_name"})
    stubber.add_response(
        "get_role_policy",
        {
            "RoleName": "role_name",
            "PolicyName": "policy1",
            "PolicyDocument": json.dumps(policy_document),
        },
        {"RoleName": "role_name", "PolicyName": "policy1"},
    )

    with stubber:
        response = await check_iam_role_state(role_arn)

    assert response == "VALID"
    mocked_get_session_credentials.assert_called_once_with(role_arn, "us-east-1")
    mocked_get_session_credentials.assert_called_once_with(role_arn, "us-east-1")
    mocked_get_iam_client.assert_called_once_with(credentials)
