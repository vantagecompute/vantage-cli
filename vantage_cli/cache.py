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
"""Token caching functionality for the Vantage CLI."""

from __future__ import annotations

import inspect
from functools import wraps
from pathlib import Path

from loguru import logger

from vantage_cli.constants import USER_TOKEN_CACHE_DIR
from vantage_cli.exceptions import Abort
from vantage_cli.schemas import TokenSet


def init_cache(cache_dir: Path) -> None:
    """Initialize cache directory."""
    try:
        USER_TOKEN_CACHE_DIR.mkdir(exist_ok=True, parents=True)
        token_dir = USER_TOKEN_CACHE_DIR / "token"
        token_dir.mkdir(exist_ok=True)
        info_file = USER_TOKEN_CACHE_DIR / "info.txt"
        info_file.write_text("This directory is used by Vantage CLI for its cache.")
    except (PermissionError, OSError, FileNotFoundError) as e:
        raise Abort(
            f"""
            Cache directory {USER_TOKEN_CACHE_DIR} doesn't exist, is not writable, or could not be created.
            Error: {e}

            Please check your home directory permissions and try again.
            """,
            subject="Non-writable cache dir",
            log_message="Non-writable cache dir",
        )


def with_cache(func):
    """Initialize cache before function execution."""
    if inspect.iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                USER_TOKEN_CACHE_DIR.mkdir(exist_ok=True, parents=True)
                token_dir = USER_TOKEN_CACHE_DIR / "token"
                token_dir.mkdir(exist_ok=True)
                info_file = USER_TOKEN_CACHE_DIR / "info.txt"
                info_file.write_text("This directory is used by Vantage CLI for its cache.")
            except (PermissionError, OSError, FileNotFoundError) as e:
                raise Abort(
                    f"""
                    Cache directory {USER_TOKEN_CACHE_DIR} doesn't exist, is not writable, or could not be created.
                    Error: {e}

                    Please check your home directory permissions and try again.
                    """,
                    subject="Non-writable cache dir",
                    log_message=f"Non-writable cache dir: {e}",
                )
            return await func(*args, **kwargs)

        return async_wrapper
    else:

        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                USER_TOKEN_CACHE_DIR.mkdir(exist_ok=True, parents=True)
                token_dir = USER_TOKEN_CACHE_DIR / "token"
                token_dir.mkdir(exist_ok=True)
                info_file = USER_TOKEN_CACHE_DIR / "info.txt"
                info_file.write_text("This directory is used by Vantage CLI for its cache.")
            except (PermissionError, OSError, FileNotFoundError) as e:
                raise Abort(
                    f"""
                    Cache directory {USER_TOKEN_CACHE_DIR} doesn't exist, is not writable, or could not be created.
                    Error: {e}

                    Please check your home directory permissions and try again.
                    """,
                    subject="Non-writable cache dir",
                    log_message="Non-writable cache dir",
                )
            return func(*args, **kwargs)

        return wrapper


def _get_token_paths(profile: str) -> tuple[Path, Path]:
    token_dir = USER_TOKEN_CACHE_DIR / profile
    access_token_path: Path = token_dir / "access.token"
    refresh_token_path: Path = token_dir / "refresh.token"
    return (access_token_path, refresh_token_path)


def load_tokens_from_cache(profile: str) -> TokenSet:
    """Load access token and refresh token from the cache."""
    (access_token_path, refresh_token_path) = _get_token_paths(profile)

    Abort.require_condition(
        access_token_path.exists(),
        "Please login with your auth token first using the `vantage login` command",
        raise_kwargs={"subject": "You need to login"},
    )

    logger.debug("Retrieving access token from cache")
    token_set: TokenSet = TokenSet(access_token=access_token_path.read_text())

    if refresh_token_path.exists():
        logger.debug("Retrieving refresh token from cache")
        token_set.refresh_token = refresh_token_path.read_text()

    return token_set


def save_tokens_to_cache(profile: str, token_set: TokenSet):
    """Save tokens from a token_set to the cache."""
    (access_token_path, refresh_token_path) = _get_token_paths(profile)
    # make sure the parent directory exists
    access_token_path.parent.mkdir(parents=True, exist_ok=True)

    logger.debug(f"Caching access token at {access_token_path}")
    access_token_path.write_text(token_set.access_token)
    access_token_path.chmod(0o600)

    if token_set.refresh_token is not None:
        logger.debug(f"Caching refresh token at {refresh_token_path}")
        refresh_token_path.write_text(token_set.refresh_token)
        refresh_token_path.chmod(0o600)


def clear_token_cache(profile: str):
    """Clear the token cache."""
    logger.debug("Clearing cached tokens")
    (access_token_path, refresh_token_path) = _get_token_paths(profile)

    logger.debug(f"Removing access token at {access_token_path}")
    if access_token_path.exists():
        access_token_path.unlink()

    logger.debug(f"Removing refresh token at {refresh_token_path}")
    if refresh_token_path.exists():
        refresh_token_path.unlink()
