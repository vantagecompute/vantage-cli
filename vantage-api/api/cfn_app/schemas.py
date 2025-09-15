"""Schemas for the Cloudformation app."""
from typing import Optional

from pydantic import BaseModel, root_validator


class AwsNetworking(BaseModel):

    """AWS networking configuration model."""

    vpc_id: str
    head_node_subnet_id: str
    compute_node_subnet_id: Optional[str] = None

    @root_validator(pre=True)
    def validate_compute_node_subnet_id(cls, values: dict):  # noqa: N805
        """Set the compute_node_subnet_id value equal to the head_node_subnet_id if not provided."""
        if values.get("compute_node_subnet_id", None) is None:
            values.setdefault("compute_node_subnet_id", values.get("head_node_subnet_id"))
        return values
