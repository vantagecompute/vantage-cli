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
"""Cudo Compute command utilities and decorators."""

import inspect
import logging
from functools import wraps
from typing import Any, Callable

import typer
from cudo_compute_sdk import CudoComputeSDK

from vantage_cli.sdk.cloud_credential.crud import cloud_credential_sdk

logger = logging.getLogger(__name__)

CLOUD = "cudo-compute"


def attach_cudo_compute_client(func: Callable[..., Any]) -> Callable[..., Any]:
    """Attach CudoComputeSDK client to the command context.

    This decorator:
    1. Retrieves the default Cudo Compute credential
    2. Initializes the CudoComputeSDK with the API key
    3. Injects the SDK as 'cudo_sdk' into the context object

    The decorated function can then access the SDK via ctx.obj.cudo_sdk.
    """
    if inspect.iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(ctx: typer.Context, *args, **kwargs):
            # Get default credential for Cudo Compute
            cudo_credential = cloud_credential_sdk.get_default(cloud_name=CLOUD)
            if cudo_credential is None:
                logger.debug(
                    f"[bold red]Error:[/bold red] No default credential found for '{CLOUD}'"
                )
                logger.debug(f"Run: vantage cloud credential create --cloud {CLOUD}")
                raise typer.Exit(code=1)

            # Initialize SDK and attach to context
            ctx.obj.cudo_sdk = CudoComputeSDK(api_key=cudo_credential.credentials_data["api_key"])

            logger.debug("CudoComputeSDK initialized and attached to context")
            return await func(ctx, *args, **kwargs)

        return async_wrapper
    else:

        @wraps(func)
        def wrapper(ctx: typer.Context, *args, **kwargs):
            # Get default credential for Cudo Compute
            cudo_credential = cloud_credential_sdk.get_default(cloud_name=CLOUD)
            if cudo_credential is None:
                logger.debug(
                    f"[bold red]Error:[/bold red] No default credential found for '{CLOUD}'"
                )
                logger.debug(f"Run: vantage cloud credential create --cloud {CLOUD}")
                raise typer.Exit(code=1)

            # Initialize SDK and attach to context
            ctx.obj.cudo_sdk = CudoComputeSDK(api_key=cudo_credential.credentials_data["api_key"])

            logger.debug("CudoComputeSDK initialized and attached to context")
            return func(ctx, *args, **kwargs)

        return wrapper
