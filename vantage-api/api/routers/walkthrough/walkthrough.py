"""Core module for defining the walkthrough router."""
from typing import Any

from armasec import TokenPayload
from fastapi import APIRouter, Depends, status
from fastapi.responses import Response
from loguru import logger

from api.body.output import MessageModel
from api.identity.management_api import backend_client
from api.settings import SETTINGS
from api.utils import response

router = APIRouter(prefix="/walkthrough")


@router.post(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Successfully marked user walkthrough as completed"},
        500: {"model": MessageModel, "description": "Unknown supported error"},
    },
)
async def mark_user_walkthrough(decoded_token: TokenPayload = Depends(SETTINGS.GUARD.lockdown())):
    """Set the user attribute `walkthrough` to True.

    This is used to determine if the user has completed the walkthrough.
    In case there's no `walkthrough` key in the user info token, it means
    neither the user has completed the walkthrough nor skipped it.
    """
    user_get_response = await backend_client.get(f"/admin/realms/vantage/users/{decoded_token.sub}")
    # it doesn't make sense to return 404 here, as the user should exist
    # because the token authentication passed
    if user_get_response.status_code != status.HTTP_200_OK:
        logger.error(f"Failed to get user info: {user_get_response.json()}")
        return response.internal_error(MessageModel(message="Failed to get user info").dict())

    user_data: dict[Any, Any] = user_get_response.json()
    user_data.update({"attributes": {"walkthrough": "true"}})

    user_put_response = await backend_client.put(
        f"/admin/realms/vantage/users/{decoded_token.sub}",
        json=user_data,
    )

    if user_put_response.status_code != status.HTTP_204_NO_CONTENT:
        logger.error(f"Failed to mark user walkthrough as completed: {user_put_response.json()}")
        return response.internal_error(
            MessageModel(message="Failed to mark user walkthrough as completed").dict()
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
