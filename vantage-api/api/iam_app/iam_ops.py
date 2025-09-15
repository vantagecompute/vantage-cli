"""Core module for AWS IAM related operations."""
import json
from collections.abc import AsyncGenerator

import boto3
import botocore.exceptions
import httpx
from mypy_boto3_iam.client import IAMClient
from mypy_boto3_iam.type_defs import PolicyDocumentDictTypeDef

from api.body.output import IamRoleStateEnum
from api.settings import SETTINGS
from api.sts_app.sts_ops import AssumedSessionCredentials, get_session_credentials


def get_iam_client(credentials: AssumedSessionCredentials) -> IAMClient:
    """Receive AWS credentials and return the IAM boto3 client."""
    iam: IAMClient = boto3.client("iam", **credentials, endpoint_url=SETTINGS.AWS_ENDPOINT_URL)
    return iam


async def fetch_upstream_policy_document() -> PolicyDocumentDictTypeDef:
    """Call an upstream endpoint and fetch the expected policy document that Vantage requires."""
    async with httpx.AsyncClient() as httpx_client:
        response = await httpx_client.get(SETTINGS.VANTAGE_INTEGRATION_POLICY_URL)
    response.raise_for_status()
    return PolicyDocumentDictTypeDef(**response.json())  # type: ignore


async def _create_policy_names_generator(policy_name_list: list[str]) -> AsyncGenerator[str, None]:
    """Generate policy names for a given IAM role."""
    for policy_name in policy_name_list:
        yield policy_name


async def check_iam_role_state(role_arn: str) -> IamRoleStateEnum:
    """Check the state of the IAM role using credentials obtained by assuming the same role."""
    try:
        session_credentials, _ = get_session_credentials(role_arn, "us-east-1")
    except botocore.exceptions.ClientError as err:
        if err.response["Error"]["Code"] == "AccessDenied":
            return IamRoleStateEnum.NOT_FOUND_OR_NOT_ACCESSIBLE

    upstream_policy_document = await fetch_upstream_policy_document()
    upstream_statements = upstream_policy_document.get("Statement")

    iam = get_iam_client(session_credentials)

    role_name = role_arn.split("/")[-1]

    try:
        inline_policies = iam.list_role_policies(RoleName=role_name)
    except botocore.exceptions.ClientError as err:
        if err.response["Error"]["Code"] == "AccessDenied":
            return IamRoleStateEnum.MISSING_PERMISSIONS

    inline_policies_names = inline_policies.get("PolicyNames")
    assert inline_policies_names is not None  # mypy assert

    async for policy_name in _create_policy_names_generator(inline_policies_names):
        try:
            role_policy = iam.get_role_policy(RoleName=role_name, PolicyName=policy_name)
        except botocore.exceptions.ClientError as err:
            if err.response["Error"]["Code"] == "AccessDenied":
                return IamRoleStateEnum.MISSING_PERMISSIONS

        policy_document = role_policy.get("PolicyDocument")
        assert policy_document is not None

        if isinstance(policy_document, str):
            # it is guaranteed that the policy document has both *Version* and *Statement* keys
            # https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies.html#access_policies-json
            policy_document = PolicyDocumentDictTypeDef(**json.loads(policy_document))  # type: ignore

        policy_statements = policy_document.get("Statement")
        assert policy_statements is not None
        assert all(isinstance(statement, dict) for statement in policy_statements)

        if any(statement not in upstream_statements for statement in policy_statements):
            return IamRoleStateEnum.MISSING_PERMISSIONS

    return IamRoleStateEnum.VALID
