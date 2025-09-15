"""Test the broker app helpers."""
import json

import pytest

from api.broker_app.helpers import create_organization_action_payload, delete_organization_action_payload


@pytest.mark.parametrize("tenant", ["dummy-tenant", "another-dummy-tenant", "yet-another-dummy-tenant"])
def test_create_organization_action_payload(tenant: str):
    """Test if the function create_organization_action_payload returns the proper result."""
    assert create_organization_action_payload(tenant) == json.dumps(
        {"tenant": tenant, "action": "create_organization"}
    ).encode("utf-8")


@pytest.mark.parametrize(
    "tenant", [("dummy-tenant",), ("another-dummy-tenant",), ("yet-another-dummy-tenant",)]
)
def test_delete_organization_action_payload(tenant: str):
    """Test if the function delete_organization_action_payload returns the proper result."""
    assert delete_organization_action_payload(tenant) == json.dumps(
        {"tenant": tenant, "action": "delete_organization"}
    ).encode("utf-8")
