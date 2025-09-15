"""Core module for AWS Marketplace Entitlement related operations."""
import boto3
from mypy_boto3_marketplace_entitlement.client import MarketplaceEntitlementServiceClient
from mypy_boto3_marketplace_entitlement.paginator import GetEntitlementsPaginator

from api.settings import SETTINGS
from api.sts_app.sts_ops import AssumedSessionCredentials, get_session_credentials


def assume_entitlement_role() -> AssumedSessionCredentials:
    """Assume the AWS Marketplace Entitlement role."""
    credentials, _ = get_session_credentials(
        SETTINGS.AWS_ROLE_NAME_MKT, region_name="us-east-1", use_custom_endpoint=False
    )
    return credentials


def get_mktplace_entitlement_client() -> MarketplaceEntitlementServiceClient:
    """Return a client for the AWS Marketplace Entitlement service."""
    credentials = assume_entitlement_role()
    return boto3.client("marketplace-entitlement", **credentials)


def get_entitlement_paginator(client: MarketplaceEntitlementServiceClient) -> GetEntitlementsPaginator:
    """Return a paginator for the AWS Marketplace Entitlement service."""
    return client.get_paginator("get_entitlements")
