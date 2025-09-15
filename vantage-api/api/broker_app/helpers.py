"""Core module for helper functions related to the broker app."""
import json
from typing import TypedDict


class OrganizationActionPayload(TypedDict):

    """Organization creation payload."""

    tenant: str
    action: str


def create_organization_action_payload(tenant: str) -> bytes:
    """Create the message broker message content based on the organization creation action."""
    payload: OrganizationActionPayload = {"tenant": tenant, "action": "create_organization"}
    return json.dumps(payload).encode("utf-8")


def delete_organization_action_payload(tenant: str) -> bytes:
    """Create the message broker message content based on the organization deletion action."""
    payload: OrganizationActionPayload = {"tenant": tenant, "action": "delete_organization"}
    return json.dumps(payload).encode("utf-8")
