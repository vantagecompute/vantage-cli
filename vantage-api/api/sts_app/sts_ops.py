"""Core module for AWS STS related operations."""
from typing import Tuple, TypedDict

import boto3
from mypy_boto3_sts import STSClient
from mypy_boto3_sts.type_defs import AssumeRoleResponseTypeDef, CredentialsTypeDef

from api.settings import SETTINGS


class AssumedSessionCredentials(TypedDict):
    """Assumed session credentials."""

    aws_access_key_id: str | None
    aws_secret_access_key: str | None
    aws_session_token: str | None
    region_name: str | None


def get_sts_client(
    credentials: AssumedSessionCredentials | dict = dict(), use_custom_endpoint: bool = True
) -> STSClient:
    """Receive AWS credentials and return the STS boto3 client."""
    if use_custom_endpoint:
        sts: STSClient = boto3.client("sts", **credentials, endpoint_url=SETTINGS.AWS_ENDPOINT_URL)
    else:
        sts: STSClient = boto3.client("sts", **credentials)
    return sts


def get_session_credentials(
    role_arn: str, region_name: str, use_custom_endpoint: bool = True
) -> Tuple[AssumedSessionCredentials, STSClient]:
    """Assume a role and return the session credentials."""
    sts = get_sts_client(use_custom_endpoint=use_custom_endpoint)
    session: AssumeRoleResponseTypeDef = sts.assume_role(
        RoleArn=role_arn,
        RoleSessionName="cluster_api_temp_session",
    )
    assumed_session_credentials: CredentialsTypeDef | None = session.get("Credentials")
    assert assumed_session_credentials is not None

    session_credentials: AssumedSessionCredentials = {
        "aws_access_key_id": assumed_session_credentials.get("AccessKeyId"),
        "aws_secret_access_key": assumed_session_credentials.get("SecretAccessKey"),
        "aws_session_token": assumed_session_credentials.get("SessionToken"),
        "region_name": region_name,
    }
    sts = get_sts_client(session_credentials)
    return session_credentials, sts
