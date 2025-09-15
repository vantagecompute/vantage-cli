"""Core module for defining schemas related to AWS."""
from enum import Enum
from typing import TypedDict


class AwsOpsConfig(TypedDict):
    """Operational configuration for AWS."""

    region_name: str | Enum
    role_arn: str
