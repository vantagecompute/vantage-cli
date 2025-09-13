# Copyright (C) 2025 Vantage Compute Corporation
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.
"""Simple async HTTP client for OAuth token operations."""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable, TypeVar

import httpx
import pydantic
import typer
from loguru import logger

from vantage_cli.exceptions import Abort


def attach_client(func: Callable) -> Callable:
    """Create async HTTP client for OAuth operations."""

    @wraps(func)
    async def wrapper(ctx: typer.Context, *args: Any, **kwargs: Any) -> Any:
        if ctx.obj.settings is None:
            raise Abort(
                "Cannot attach client before settings!",
                subject="Configuration Error",
                log_message="Settings not configured before client attachment",
            )

        logger.debug("Creating async HTTP client for OAuth operations")
        async with httpx.AsyncClient(
            base_url=ctx.obj.settings.oidc_base_url,
            headers={"content-type": "application/x-www-form-urlencoded"},
        ) as client:
            ctx.obj.client = client
            return await func(ctx, *args, **kwargs)

    return wrapper


ResponseModel = TypeVar("ResponseModel", bound=pydantic.BaseModel)


async def make_oauth_request(
    client: httpx.AsyncClient,
    url_path: str,
    data: dict[str, Any],
    response_model_cls: type[ResponseModel],
    abort_message: str = "OAuth request failed",
    abort_subject: str = "AUTHENTICATION ERROR",
) -> ResponseModel:
    """Make an async OAuth token request.

    Simplified version focused only on OAuth POST requests with form data.
    """
    logger.debug(f"Making OAuth request to {url_path}")

    try:
        response = await client.post(url_path, data=data)
        response.raise_for_status()

        response_data = response.json()
        logger.debug(f"OAuth response received: {response_data}")

        return response_model_cls(**response_data)

    except httpx.HTTPStatusError as e:
        logger.error(
            f"OAuth request failed with status {e.response.status_code}: {e.response.text}"
        )
        if abort_message == "IGNORE":
            raise e
        raise Abort(
            f"{abort_message}: Received error response",
            subject=abort_subject,
            log_message=f"OAuth request failed: {e.response.status_code} - {e.response.text}",
        )
    except (httpx.RequestError, httpx.ConnectError, httpx.TimeoutException) as e:
        logger.error(f"OAuth request failed: {e}")
        if abort_message == "IGNORE":
            raise e
        raise Abort(
            f"{abort_message}: Request failed",
            subject=abort_subject,
            log_message=f"OAuth request error: {e}",
        )
