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
"""Configuration settings for Vantage CLI."""

import inspect
import json
import os
import shutil
from asyncio.log import logger
from functools import wraps
from typing import Any, Callable, Optional

import typer
from pydantic import BaseModel, ValidationError, computed_field

from .constants import (
    USER_CONFIG_FILE,
    USER_TOKEN_CACHE_DIR,
    VANTAGE_CLI_ACTIVE_PROFILE,
    VANTAGE_CLI_LOCAL_USER_BASE_DIR,
)


class Settings(BaseModel):
    """Configuration settings for the Vantage CLI."""

    supported_clouds: list[str] = [
        "maas",
        "localhost",
        "aws",
        "gcp",
        "azure",
        "on-premises",
        "k8s",
    ]
    api_base_url: str = "https://apis.vantagecompute.ai"
    oidc_base_url: str = "https://auth.vantagecompute.ai"
    tunnel_api_url: str = "https://tunnel.vantagecompute.ai"
    oidc_client_id: str = "default"
    oidc_max_poll_time: int = 5 * 60  # 5 minutes

    @computed_field
    @property
    def dev_apps_gh_url(self) -> Optional[str]:
        """Construct the GitHub URL for the dev apps repository."""
        if gh_pat := os.environ.get("GH_PAT"):
            return f"https://{gh_pat}@github.com/vantagecompute/vantage-cli-dev-apps.git"
        return None

    @computed_field
    @property
    def oidc_domain(self) -> str:
        """Extract the domain from the OIDC base URL."""
        return self.oidc_base_url.split("//")[-1] + "/realms/vantage"

    @computed_field
    @property
    def oidc_token_url(self) -> str:
        """Construct the OIDC token URL from the base URL."""
        return f"{self.oidc_base_url}/realms/vantage/protocol/openid-connect/token"


def init_user_filesystem(profile: str) -> None:
    """Initialize the user filesystem directories for a profile."""
    (USER_TOKEN_CACHE_DIR / profile).mkdir(parents=True, exist_ok=True)


def init_settings(**settings_values) -> Settings:
    """Initialize settings with validation."""
    try:
        logger.debug("Validating settings")
        return Settings(**settings_values)
    except ValidationError as e:
        logger.error(f"Settings validation error: {e}")
        raise


def attach_settings(func: Callable[..., Any]) -> Callable[..., Any]:
    """Attach settings to the CLI context."""
    if inspect.iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(ctx: typer.Context, *args, **kwargs):
            try:
                logger.debug(f"Loading settings from {USER_CONFIG_FILE}")
                settings_all_profiles = json.loads(USER_CONFIG_FILE.read_text())
                settings_values = settings_all_profiles.get(ctx.obj.profile)
            except FileNotFoundError:
                logger.error("Settings file missing!")
                typer.echo(
                    f"""
                    No settings file found at {USER_CONFIG_FILE}!

                    Run the set-config sub-command first to establish your OIDC settings.
                    """
                )
                raise typer.Exit(1)
            logger.debug("Binding settings to CLI context")
            ctx.obj.settings = init_settings(**(settings_values or {}))
            return await func(ctx, *args, **kwargs)

        return async_wrapper
    else:

        @wraps(func)
        def wrapper(ctx: typer.Context, *args, **kwargs):
            try:
                logger.debug(f"Loading settings from {USER_CONFIG_FILE}")
                settings_all_profiles = json.loads(USER_CONFIG_FILE.read_text())
                settings_values = settings_all_profiles.get(ctx.obj.profile)
            except FileNotFoundError:
                logger.error("Settings file missing!")
                typer.echo(
                    f"""
                    No settings file found at {USER_CONFIG_FILE}!

                    Run the set-config sub-command first to establish your OIDC settings.
                    """
                )
                raise typer.Exit(1)
            logger.debug("Binding settings to CLI context")
            ctx.obj.settings = init_settings(**(settings_values or {}))
            return func(ctx, *args, **kwargs)

    return wrapper


def dump_settings(profile: str, settings: Settings) -> None:
    """Save settings to the user configuration file."""
    logger.debug(f"Saving settings to {USER_CONFIG_FILE}")
    if USER_CONFIG_FILE.exists():
        settings_all_profiles = json.loads(USER_CONFIG_FILE.read_text())
    else:
        settings_all_profiles = {}

    settings_all_profiles[f"{profile}"] = settings.model_dump()
    USER_CONFIG_FILE.write_text(json.dumps(settings_all_profiles))


def clear_settings() -> None:
    """Remove the entire Vantage CLI local user directory."""
    logger.debug(f"Removing entire Vantage CLI directory at {VANTAGE_CLI_LOCAL_USER_BASE_DIR}")
    try:
        shutil.rmtree(VANTAGE_CLI_LOCAL_USER_BASE_DIR)
        logger.debug(f"Removed Vantage CLI directory at {VANTAGE_CLI_LOCAL_USER_BASE_DIR}")
    except FileNotFoundError:
        logger.debug("Vantage CLI directory already absent; nothing to remove")


def ensure_default_profile_exists() -> None:
    """Ensure the default profile exists and is properly configured."""
    if VANTAGE_CLI_LOCAL_USER_BASE_DIR.exists() is False:
        VANTAGE_CLI_LOCAL_USER_BASE_DIR.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Created local user base directory at {VANTAGE_CLI_LOCAL_USER_BASE_DIR}")

    if not USER_CONFIG_FILE.exists():
        # Create the default profile with default settings
        logger.debug("Creating default profile on first run")
        default_settings = Settings()
        dump_settings("default", default_settings)


def get_active_profile() -> str:
    """Get the currently active profile name."""
    if VANTAGE_CLI_ACTIVE_PROFILE.exists():
        try:
            return VANTAGE_CLI_ACTIVE_PROFILE.read_text().strip()
        except (FileNotFoundError, PermissionError):
            pass
    return "default"


def set_active_profile(profile_name: str) -> None:
    """Set the active profile."""
    VANTAGE_CLI_ACTIVE_PROFILE.parent.mkdir(parents=True, exist_ok=True)
    VANTAGE_CLI_ACTIVE_PROFILE.write_text(profile_name)
