"""Core module for AWS Marketplace Metering related operations."""
import boto3
from mypy_boto3_meteringmarketplace.client import MarketplaceMeteringClient

from api.settings import SETTINGS
from api.sts_app.sts_ops import AssumedSessionCredentials, get_session_credentials


def _assume_mkt_role() -> AssumedSessionCredentials:
    """Assume the AWS Marketplace Metering role."""
    credentials, _ = get_session_credentials(
        SETTINGS.AWS_ROLE_NAME_MKT, region_name="us-east-1", use_custom_endpoint=False
    )
    return credentials


def get_metering_mkt_client() -> MarketplaceMeteringClient:
    """Return a client for the AWS Marketplace Metering service."""
    credentials = _assume_mkt_role()
    return boto3.client("meteringmarketplace", **credentials)
