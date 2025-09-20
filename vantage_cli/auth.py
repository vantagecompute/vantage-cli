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
"""Authentication and authorization functionality for the Vantage CLI."""

import asyncio
import datetime
import json
from typing import Any, Union

import httpx
import snick
import typer
from jose import jwt
from jose.exceptions import ExpiredSignatureError
from loguru import logger
from pydantic import ValidationError

from vantage_cli.cache import load_tokens_from_cache, save_tokens_to_cache
from vantage_cli.client import make_oauth_request
from vantage_cli.config import Settings
from vantage_cli.constants import USER_CONFIG_FILE
from vantage_cli.exceptions import Abort
from vantage_cli.render import terminal_message
from vantage_cli.schemas import CliContext, DeviceCodeData, IdentityData, Persona, TokenSet
from vantage_cli.time_loop import TimeLoop


def extract_persona(
    profile: str, token_set: TokenSet | None = None, settings: Union["Settings", None] = None
):
    """Extract user persona from cached tokens or provided token set."""
    if token_set is None:
        token_set = load_tokens_from_cache(profile)

    # Check token expiration and refresh if needed before attempting validation
    token_set = refresh_token_if_needed(profile, token_set)

    # Now validate and extract identity from the (potentially refreshed) token
    identity_data = validate_token_and_extract_identity(token_set)

    logger.debug(f"Persona created with identity_data: {identity_data}")

    save_tokens_to_cache(profile, token_set)

    return Persona(
        token_set=token_set,
        identity_data=identity_data,
    )


def validate_token_and_extract_identity(token_set: TokenSet) -> IdentityData:
    """Validate access token and extract user identity information."""
    logger.debug("Validating access token")

    token_file_is_empty = not token_set.access_token
    if token_file_is_empty:
        logger.debug("Access token file exists but it is empty")
        raise Abort(
            """
            Access token file exists but it is empty.

            Please try logging in again.
            """,
            subject="Empty access token file",
            log_message="Empty access token file",
        )

    with Abort.handle_errors(
        """
        There was an unknown error while validating the access token.

        Please try logging in again.
        """,
        ignore_exc_class=ExpiredSignatureError,  # Will be handled in calling context
        raise_kwargs={
            "subject": "Invalid access token",
            "log_message": "Unknown error while validating access access token",
        },
    ):
        token_data = jwt.decode(
            token_set.access_token,
            "",  # Empty key is acceptable when verify_signature is False
            options={
                "verify_signature": False,
                "verify_aud": False,
                "verify_exp": True,
            },
        )

    logger.debug("Extracting identity data from the access token")
    with Abort.handle_errors(
        """
        There was an error extracting the user's identity from the access token.

        Please try logging in again.
        """,
        handle_exc_class=ValidationError,
        raise_kwargs={
            "subject": "Missing user data",
            "log_message": "Token data could not be extracted to identity",
        },
    ):
        identity = IdentityData(
            email=token_data.get("email"),
            client_id=token_data.get("azp") or "unknown",
        )

    return identity


def is_token_expired(token: str, buffer_seconds: int = 60) -> bool:
    """Check if a JWT token is expired or will expire within buffer_seconds.

    Args:
        token: JWT access token
        buffer_seconds: Number of seconds before actual expiry to consider token expired

    Returns:
        True if token is expired or will expire soon, False otherwise
    """
    try:
        # Decode token without verification to get expiration
        token_data = jwt.decode(
            token,
            "",  # Empty key is acceptable when verify_signature is False
            options={
                "verify_signature": False,
                "verify_aud": False,
                "verify_exp": False,  # Don't verify expiration here, we want to check manually
            },
        )

        if "exp" not in token_data:
            logger.debug("Token does not contain expiration claim")
            return True  # Consider token expired if no expiration claim

        exp_timestamp = token_data["exp"]
        exp_datetime = datetime.datetime.fromtimestamp(exp_timestamp)
        now_with_buffer = datetime.datetime.now() + datetime.timedelta(seconds=buffer_seconds)

        is_expired = exp_datetime <= now_with_buffer

        if is_expired:
            logger.debug(
                f"Token expired or will expire soon. Expires at: {exp_datetime}, Current time + buffer: {now_with_buffer}"
            )
        else:
            logger.debug(
                f"Token is valid. Expires at: {exp_datetime}, Current time + buffer: {now_with_buffer}"
            )

        return is_expired

    except Exception as e:
        logger.debug(f"Error checking token expiration: {e}")
        return True  # Consider token expired if we can't parse it


def refresh_token_if_needed(profile: str, token_set: TokenSet) -> TokenSet:
    """Check if the access token is expired and refresh it if needed.

    Args:
        profile: Profile name for token caching
        token_set: Current token set

    Returns:
        Updated token set with refreshed tokens if refresh was needed
    """
    if not token_set.access_token:
        logger.debug("No access token available")
        return token_set

    if not is_token_expired(token_set.access_token):
        logger.debug("Access token is still valid")
        return token_set

    logger.debug("Access token is expired, attempting refresh")

    if not token_set.refresh_token:
        logger.debug("No refresh token available")
        raise Abort(
            "The access token is expired and no refresh token is available. Please log in again.",
            subject="Token expired",
            log_message="Token expired and no refresh token available",
        )

    try:
        # Load settings for the refresh operation
        if USER_CONFIG_FILE.exists():
            settings_all_profiles = json.loads(USER_CONFIG_FILE.read_text())
            settings_values = settings_all_profiles.get(profile, {})

            settings = Settings(**settings_values)
        else:
            # Use default settings if no config file exists
            settings = Settings()

        # Attempt to refresh the token
        refresh_success = refresh_access_token_standalone(token_set, settings)

        if refresh_success:
            logger.debug("Successfully refreshed access token")
            # Save the updated tokens to cache
            save_tokens_to_cache(profile, token_set)
            return token_set
        else:
            raise Exception("Token refresh returned False")

    except Exception as e:
        logger.error(f"Failed to refresh token: {e}")
        raise Abort(
            "Failed to refresh the expired access token. Please log in again.",
            subject="Token refresh failed",
            log_message=f"Token refresh failed: {e}",
        )


def init_persona(ctx: typer.Context, token_set: TokenSet | None = None):
    """Initialize persona from cached tokens or provided token set."""
    if token_set is None:
        token_set = load_tokens_from_cache(profile=ctx.obj.profile)

    try:
        identity_data = validate_token_and_extract_identity(token_set)
    except ExpiredSignatureError:
        Abort.require_condition(
            token_set.refresh_token is not None,
            "The auth token is expired. Please retrieve a new and log in again.",
            raise_kwargs={
                "subject": "Expired access token",
            },
        )

        logger.debug("The access token is expired. Attempting to refresh token")
        # Use standalone refresh since this function is not async
        if hasattr(ctx.obj, "settings") and ctx.obj.settings:
            settings = ctx.obj.settings
        else:
            settings = Settings()  # Use default settings
        refresh_success = refresh_access_token_standalone(token_set, settings)
        if not refresh_success:
            raise Exception("Failed to refresh access token")
        identity_data = validate_token_and_extract_identity(token_set)

    logger.debug(f"Persona created with identity_data: {identity_data}")

    save_tokens_to_cache(ctx.obj.profile, token_set)

    return Persona(
        token_set=token_set,
        identity_data=identity_data,
    )


def refresh_access_token_standalone(token_set: TokenSet, settings: "Settings") -> bool:
    """Attempt to fetch a new access token given a refresh token.

    Returns True if refresh was successful, False otherwise.
    Sets the access token in-place.
    """
    if not token_set.refresh_token:
        return False

    url = f"{settings.oidc_base_url}/realms/vantage/protocol/openid-connect/token"
    logger.debug(f"Requesting refreshed access token from {url}")

    try:
        with httpx.Client() as client:
            response = client.post(
                url,
                data={
                    "client_id": settings.oidc_client_id,
                    "grant_type": "refresh_token",
                    "refresh_token": token_set.refresh_token,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30.0,
            )
            response.raise_for_status()

            token_data = response.json()
            token_set.access_token = token_data["access_token"]

            # Update refresh token if provided
            if "refresh_token" in token_data:
                token_set.refresh_token = token_data["refresh_token"]

            logger.debug("Successfully refreshed access token")
            return True

    except Exception as e:
        logger.error(f"Failed to refresh token: {e}")
        return False


async def refresh_access_token(ctx: CliContext, token_set: TokenSet):
    """Attempt to fetch a new access token given a refresh token in a token_set.

    Sets the access token in-place.

    If refresh fails, notify the user that they need to log in again.
    """
    if ctx.client is None:
        raise RuntimeError("HTTP client not initialized")
    if ctx.settings is None:
        raise RuntimeError("Settings not initialized")

    url = "/realms/vantage/protocol/openid-connect/token"
    logger.debug(f"Requesting refreshed access token from {url}")

    refreshed_token_set: TokenSet = await make_oauth_request(
        ctx.client,
        url,
        data={
            "client_id": ctx.settings.oidc_client_id,
            "grant_type": "refresh_token",
            "refresh_token": token_set.refresh_token,
        },
        response_model_cls=TokenSet,
        abort_message="The auth token could not be refreshed. Please try logging in again.",
        abort_subject="EXPIRED ACCESS TOKEN",
    )

    token_set.access_token = refreshed_token_set.access_token


async def fetch_auth_tokens(ctx: CliContext) -> TokenSet:
    """Fetch an access token (and possibly a refresh token) from Auth0.

    Prints out a URL for the user to use to authenticate and polls the token endpoint to fetch it
    when the browser-based process finishes.
    """
    if ctx.client is None:
        raise RuntimeError("HTTP client not initialized")
    if ctx.settings is None:
        raise RuntimeError("Settings not initialized")

    device_path = "/realms/vantage/protocol/openid-connect/auth/device"
    token_path = "/realms/vantage/protocol/openid-connect/token"

    device_code_data: DeviceCodeData = await make_oauth_request(
        ctx.client,
        device_path,
        data={
            "client_id": ctx.settings.oidc_client_id,
        },
        response_model_cls=DeviceCodeData,
        abort_message=(
            """
            There was a problem retrieving a device verification code from
            the auth provider
            """
        ),
        abort_subject="COULD NOT RETRIEVE TOKEN",
    )

    max_poll_time = 5 * 60  # 5 minutes
    terminal_message(
        f"""
        To complete login, please open the following link in a browser:

          {device_code_data.verification_uri_complete}

        Waiting up to {max_poll_time / 60} minutes for you to complete the process...
        """,
        subject="Waiting for login",
    )

    for tick in TimeLoop(
        ctx.settings.oidc_max_poll_time,
        message="Waiting for web login",
    ):
        # For polling, we need to handle error responses as dict, not TokenSet
        response_data: dict[str, Any] = {}
        try:
            # Attempt to get a successful token response
            token_data = await make_oauth_request(
                ctx.client,
                token_path,
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    "device_code": device_code_data.device_code,
                    "client_id": ctx.settings.oidc_client_id,
                },
                response_model_cls=TokenSet,
                abort_message="IGNORE",  # We'll handle errors manually
                abort_subject="IGNORE",
            )
            return token_data
        except Exception:
            # If it fails, make a raw request to get the error details
            response = await ctx.client.post(
                f"{ctx.settings.oidc_base_url}{token_path}",
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    "device_code": device_code_data.device_code,
                    "client_id": ctx.settings.oidc_client_id,
                },
            )
            response_data = response.json()

        if "error" in response_data:
            if response_data["error"] == "authorization_pending":
                logger.debug(f"Token fetch attempt #{tick.counter} failed")
                logger.debug(f"Will try again in {device_code_data.interval} seconds")
                await asyncio.sleep(device_code_data.interval)
            elif response_data["error"] == "slow_down":
                logger.debug(f"Server requested slow down on attempt #{tick.counter}")
                logger.debug(f"Will try again in {device_code_data.interval * 2} seconds")
                await asyncio.sleep(device_code_data.interval * 2)
            else:
                # TODO: Test this failure condition
                raise Abort(
                    snick.unwrap(
                        """
                        There was a problem retrieving a device verification code
                        from the auth provider:
                        Unexpected failure retrieving access token.
                        """
                    ),
                    subject="Unexpected error",
                    log_message=f"Unexpected error response: {response_data}",
                )
        else:
            return TokenSet(**response_data)

    raise Abort(
        "Login process was not completed in time. Please try again.",
        subject="Timed out",
        log_message="Timed out while waiting for user to complete login",
    )
