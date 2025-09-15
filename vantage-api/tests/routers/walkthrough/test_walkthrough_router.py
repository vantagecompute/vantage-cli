"""Core module containing tests for the walkthrough router.

It tests if the user attribute can be patched to indicate the user has been through the walkthrough
and if the endpoint returns 500 when an unexpected error happens.
"""
from collections.abc import Callable

import pytest
from fastapi import status
from httpx import AsyncClient, Response
from respx.router import MockRouter

from api.identity.management_api import backend_client


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
@pytest.mark.parametrize(
    "sub",
    [("me"), ("me2"), ("me3"), ("dummy-sub")],
)
async def test_mark_user_walkthrough(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    sub: str,
    requester_email: str,
):
    """Test if user attribute can be patched to indicate the user has been through the walkthrough."""
    respx_mock.get(f"/admin/realms/vantage/users/{sub}").mock(
        return_value=Response(200, json={"email": requester_email})
    )
    payload = {"email": requester_email, "attributes": {"walkthrough": "true"}}
    respx_mock.put(f"/admin/realms/vantage/users/{sub}", json=payload).mock(return_value=Response(204))

    inject_security_header(sub)
    response = await test_client.post("/admin/management/walkthrough")

    assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
@pytest.mark.parametrize(
    "sub",
    [("me"), ("me2"), ("me3"), ("dummy-sub")],
)
async def test_mark_user_walkthrough__fail_upon_unknown_error(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    sub: str,
):
    """Test if user attribute can be patched to indicate the user has been through the walkthrough."""
    respx_mock.get(f"/admin/realms/vantage/users/{sub}").mock(
        return_value=Response(500, json={"error": "unknown"})
    )

    inject_security_header(sub)
    response = await test_client.post("/admin/management/walkthrough")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json().get("message") == "Failed to get user info"


@pytest.mark.asyncio
@pytest.mark.respx(base_url=str(backend_client.base_url))
@pytest.mark.parametrize(
    "sub",
    [("me"), ("me2"), ("me3"), ("dummy-sub")],
)
async def test_fail_mark_user_walkthrough(
    respx_mock: MockRouter,
    inject_security_header: Callable,
    test_client: AsyncClient,
    sub: str,
    requester_email: str,
):
    """Test if the endpoint returns 500 when a unexpected error happens."""
    respx_mock.get(f"/admin/realms/vantage/users/{sub}").mock(
        return_value=Response(200, json={"email": requester_email})
    )
    payload = {"email": requester_email, "attributes": {"walkthrough": "true"}}
    respx_mock.put(f"/admin/realms/vantage/users/{sub}", json=payload).mock(
        return_value=Response(500, json={"error": "dummy"})
    )

    inject_security_header(sub)
    response = await test_client.post("/admin/management/walkthrough")
    response_json = response.json()

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response_json.get("message") == "Failed to mark user walkthrough as completed"
