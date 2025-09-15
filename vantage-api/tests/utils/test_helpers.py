"""Tests for the helpers module."""
import json
from unittest import mock

import pytest
from fastapi import HTTPException, status
from httpx import Response
from respx.router import MockRouter

from api.body.output import UserListModel, UserModel
from api.identity.management_api import backend_client
from api.utils.helpers import (
    fetch_default_client,
    fetch_users_count,
    mount_users_list,
    unpack_organization_id_from_token,
)


def test_mount_users_list__check_if_output_inherits_pydantic_model():
    """Check if the output inherits from a Pydantic model."""
    assert isinstance(mount_users_list([]), UserListModel)


def test_mount_users_list__check_if_empty_input_returns_empty_output():
    """Check if the output is empty when the input is empty while mouting a list of users."""
    users_list = mount_users_list([])

    assert users_list.users == []


def test_mount_users_list__check_correct_output(dummy_user_list):
    """Check if the output is correct when mounting a list of users."""
    users_list = mount_users_list(dummy_user_list)

    assert len(users_list.users) == 3
    assert users_list.users[0].dict() == {
        "user_id": "dc60a026-631a-49f9-a837-45d6287f252f",
        "email": "angry.bull@omnivector.solutions",
        "name": "Angry Bull",
        "avatar_url": "https://avatar.com/angry-bull",
    }
    assert users_list.users[1].dict() == {
        "user_id": "a5f6fd56-8161-4150-a34a-7a62cedb0483",
        "email": "beautiful.shark@omnivector.solutions",
        "name": "Beautiful Shark",
        "avatar_url": "https://avatar.com/beautiful-shark",
    }
    assert users_list.users[2].dict() == {
        "user_id": "a282a8e0-d3b9-4a7d-ade2-7c226806e0d6",
        "email": "happy.ant@omnivector.solutions",
        "name": None,
        "avatar_url": "https://avatar.com/happy-bull",
    }


def test_mount_users_list__check_correct_output_when_user_hasnt_all_properties_set(dummy_user_list):
    """Check if the output is correct when the user hasn't all properties set."""
    user = dummy_user_list[0]

    user.update(firstName=None)

    users_list = mount_users_list([user])

    assert len(users_list.users) == 1
    assert users_list.users[0].dict() == {
        "user_id": "dc60a026-631a-49f9-a837-45d6287f252f",
        "email": "angry.bull@omnivector.solutions",
        "name": "Bull",
        "avatar_url": "https://avatar.com/angry-bull",
    }

    user.update(firstName="Angry", lastName=None)

    users_list = mount_users_list([user])

    assert len(users_list.users) == 1
    assert users_list.users[0].dict() == {
        "user_id": "dc60a026-631a-49f9-a837-45d6287f252f",
        "email": "angry.bull@omnivector.solutions",
        "name": "Angry",
        "avatar_url": "https://avatar.com/angry-bull",
    }

    user.update(firstName=None, lastName=None)

    users_list = mount_users_list([user])

    assert len(users_list.users) == 1
    assert users_list.users[0].dict() == {
        "user_id": "dc60a026-631a-49f9-a837-45d6287f252f",
        "email": "angry.bull@omnivector.solutions",
        "name": None,
        "avatar_url": "https://avatar.com/angry-bull",
    }


def test_mount_users_list__check_if_each_element_is_pydantic_instance(dummy_user_list):
    """Check if each element in the list is a Pydantic instance."""
    users_list = mount_users_list(dummy_user_list)

    assert all((isinstance(user, UserModel) for user in users_list.users))


@pytest.mark.asyncio
async def test_fetch_default_client(mock_fetch_default_client, default_client):
    """Check if the default client is fetched correctly."""
    fetched_default_client = await fetch_default_client()
    assert fetched_default_client == default_client


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
@mock.patch("api.utils.helpers.logger")
async def test_fetch_default_client__check_if_api_raises_error_when_no_client_is_fetched(
    mocked_logger, respx_mock
):
    """Check if the API raises an error when no client is fetched."""
    response_text = "This is a dummy text for testing whether it is logged or not"
    payload = {"error": response_text}
    respx_mock.get("/admin/realms/vantage/clients", params={"clientId": "default"}).mock(
        return_value=Response(404, json=payload, text=json.dumps(payload))
    )

    mocked_logger.critical = mock.Mock()

    with pytest.raises(HTTPException) as err:
        await fetch_default_client()

    assert err.value.status_code == status.HTTP_502_BAD_GATEWAY
    assert err.value.detail == "Unknown error, contact support"
    mocked_logger.critical.assert_called_once_with(
        f"Unknown error fetching default client: {json.dumps(payload)}"
    )


def test_unpack_organization_id_from_token__check_if_organization_id_is_extracted_from_token():
    """Check if the organization ID is extracted from the token."""
    expected_organization_id = "068c6a69-aa62-4ce3-a9d0-da036e2f0001"
    org_name = "omnivector"

    mocked_token = mock.Mock()
    mocked_token.organization = {
        org_name: {
            "name": "omnivector",
            "id": expected_organization_id,
            "attributes": {"created_at": ["123456"], "logo": ["https://dummy-logo.com"]},
        }
    }

    result_organization_id = unpack_organization_id_from_token(mocked_token)

    assert expected_organization_id == result_organization_id


def test_unpack_organization_id_from_token__check_when_no_organization_in_token():
    """Raise an AssertionError in case the payload in the token is malformed."""
    mocked_token = mock.Mock()
    mocked_token.organization = None

    with pytest.raises(AssertionError):
        unpack_organization_id_from_token(mocked_token)


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
@pytest.mark.parametrize(
    "number_of_users, number_of_clients",
    [(10, 7), (20, 9), (30, 14), (28, 27)],
)
async def test_fetch_users_count(number_of_users: int, number_of_clients: int, respx_mock: MockRouter):
    """Verify if the users count is fetched correctly."""
    organization_id = "test_organization_id"

    respx_mock.get(f"/admin/realms/vantage/organizations/{organization_id}/members/count").mock(
        return_value=Response(200, json=number_of_users)
    )
    respx_mock.get(
        "/admin/realms/vantage/clients", params={"clientId": organization_id, "search": True}
    ).mock(return_value=Response(200, json=[{}] * number_of_clients))

    count = await fetch_users_count(organization_id)
    assert count == number_of_users - number_of_clients
