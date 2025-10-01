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
"""Profile CRUD SDK using the base local resource classes."""

import json
from typing import Any, Dict, List, Optional

import typer
from loguru import logger

from vantage_cli.cache import clear_token_cache
from vantage_cli.config import (
    Settings,
    dump_settings,
    get_active_profile,
    init_user_filesystem,
    set_active_profile,
)
from vantage_cli.constants import USER_CONFIG_FILE, USER_TOKEN_CACHE_DIR
from vantage_cli.exceptions import Abort
from vantage_cli.sdk.profile.schema import Profile
from vantage_cli.sdk.base import BaseLocalResourceSDK


class ProfileSDK(BaseLocalResourceSDK):
    """SDK for profile CRUD operations using local configuration files."""

    def __init__(self):
        super().__init__(resource_name="profile", config_file_path=str(USER_CONFIG_FILE))

    def _load_all_resources(self) -> Dict[str, Any]:
        """Load all profiles from the config file."""
        if not USER_CONFIG_FILE.exists():
            return {}

        try:
            return json.loads(USER_CONFIG_FILE.read_text())
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save_resource(self, resource_id: str, resource_data: Dict[str, Any]) -> None:
        """Save a profile to the config file."""
        all_profiles = self._load_all_resources()
        all_profiles[resource_id] = resource_data

        USER_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        USER_CONFIG_FILE.write_text(json.dumps(all_profiles, indent=2))

    def _delete_resource(self, resource_id: str) -> None:
        """Delete a profile from the config file."""
        all_profiles = self._load_all_resources()

        if resource_id in all_profiles:
            del all_profiles[resource_id]
            USER_CONFIG_FILE.write_text(json.dumps(all_profiles, indent=2))

        # Clear token cache for this profile
        self._clear_profile_token_cache(resource_id)

        # Remove profile token cache directory if it exists
        profile_cache_dir = USER_TOKEN_CACHE_DIR / resource_id
        if profile_cache_dir.exists():
            import shutil

            shutil.rmtree(profile_cache_dir)

    async def list(self, ctx: typer.Context, **kwargs: Any) -> List[Dict[str, Any]]:
        """List all profiles as dict data (base class compatibility).

        Args:
            ctx: Typer context
            **kwargs: Additional parameters

        Returns:
            List of profile data dictionaries
        """
        profiles = await self.get_profiles(ctx, **kwargs)
        return [profile.model_dump() for profile in profiles]

    async def get_profiles(self, ctx: typer.Context, **kwargs: Any) -> List[Profile]:
        """Get all profiles as Profile objects.

        Args:
            ctx: Typer context
            **kwargs: Additional parameters

        Returns:
            List of Profile objects
        """
        all_profiles_raw = self._load_all_resources()
        active_profile = get_active_profile()

        profiles: List[Profile] = []
        for profile_name, settings_data in all_profiles_raw.items():
            try:
                settings = Settings(**settings_data)
                profile = Profile(
                    name=profile_name,
                    settings=settings,
                    is_active=(profile_name == active_profile),
                )
                profiles.append(profile)
            except Exception as e:
                logger.warning(f"Failed to load profile '{profile_name}': {e}")
                continue

        return profiles

    async def get_profile(
        self, ctx: typer.Context, profile_name: str, **kwargs: Any
    ) -> Optional[Profile]:
        """Get a specific profile as a Profile object.

        Args:
            ctx: Typer context
            profile_name: Name of the profile to retrieve
            **kwargs: Additional parameters

        Returns:
            Profile object or None if not found
        """
        all_profiles_raw = self._load_all_resources()

        if profile_name not in all_profiles_raw:
            return None

        try:
            settings_data = all_profiles_raw[profile_name]
            settings = Settings(**settings_data)
            active_profile = get_active_profile()

            return Profile(
                name=profile_name, settings=settings, is_active=(profile_name == active_profile)
            )
        except Exception as e:
            logger.error(f"Failed to load profile '{profile_name}': {e}")
            return None

    def _clear_profile_token_cache(self, profile_name: str) -> None:
        """Clear cached tokens for a profile."""
        try:
            clear_token_cache(profile_name)
        except Exception as e:
            logger.warning(f"Failed to clear token cache for profile '{profile_name}': {e}")

    async def create(
        self, ctx: typer.Context, resource_data: Dict[str, Any], **kwargs: Any
    ) -> Dict[str, Any]:
        """Create a new profile.

        Args:
            ctx: Typer context
            resource_data: Profile data including settings
            **kwargs: Additional options like force, activate, etc.

        Returns:
            Created profile data
        """
        profile_name = resource_data.get("name")
        if not profile_name:
            raise Abort("Profile name is required", subject="Invalid Profile Data")

        force = kwargs.get("force", False)
        activate = kwargs.get("activate", False)

        # Check if profile already exists
        existing_profiles = self._load_all_resources()

        if profile_name in existing_profiles and not force:
            raise Abort(
                f"Profile '{profile_name}' already exists. Use force=True to overwrite.",
                subject="Profile Exists",
                log_message=f"Profile '{profile_name}' already exists",
            )

        try:
            # Create settings object
            settings_data = resource_data.get("settings", {})
            settings = Settings(
                vantage_url=settings_data.get("vantage_url", "https://app.vantagecompute.ai"),
                oidc_max_poll_time=settings_data.get("oidc_max_poll_time", 300),
            )

            # Initialize filesystem for this profile
            init_user_filesystem(profile_name)

            # Save the settings
            dump_settings(profile_name, settings)

            # Set as active profile if requested
            if activate:
                set_active_profile(profile_name)
                logger.info(f"Set '{profile_name}' as active profile")

            logger.info(f"Created profile '{profile_name}'")

            return {
                "name": profile_name,
                "settings": settings.model_dump(),
                "is_active": activate,
            }

        except Exception as e:
            logger.error(f"Failed to create profile '{profile_name}': {str(e)}")
            raise Abort(
                f"Failed to create profile '{profile_name}': {str(e)}",
                subject="Profile Creation Failed",
                log_message=f"Profile creation error: {str(e)}",
            )

    async def update(
        self, ctx: typer.Context, resource_id: str, resource_data: Dict[str, Any], **kwargs: Any
    ) -> Dict[str, Any]:
        """Update an existing profile.

        Args:
            ctx: Typer context
            resource_id: Profile name
            resource_data: Updated profile data
            **kwargs: Additional parameters

        Returns:
            Updated profile data
        """
        existing_profiles = self._load_all_resources()

        if resource_id not in existing_profiles:
            raise Abort(
                f"Profile '{resource_id}' does not exist.",
                subject="Profile Not Found",
                log_message=f"Profile '{resource_id}' not found for update",
            )

        try:
            # Update the profile settings
            current_settings = existing_profiles[resource_id]
            updated_settings = {**current_settings, **resource_data.get("settings", {})}

            settings = Settings(**updated_settings)
            dump_settings(resource_id, settings)

            logger.info(f"Updated profile '{resource_id}'")

            return {
                "name": resource_id,
                "settings": settings.model_dump(),
            }

        except Exception as e:
            logger.error(f"Failed to update profile '{resource_id}': {str(e)}")
            raise Abort(
                f"Failed to update profile '{resource_id}': {str(e)}",
                subject="Profile Update Failed",
                log_message=f"Profile update error: {str(e)}",
            )

    async def delete(self, ctx: typer.Context, resource_id: str, **kwargs: Any) -> bool:
        """Delete a profile.

        Args:
            ctx: Typer context
            resource_id: Profile name
            **kwargs: Additional parameters like force

        Returns:
            True if deletion was successful
        """
        force = kwargs.get("force", False)

        existing_profiles = self._load_all_resources()

        if resource_id not in existing_profiles:
            raise Abort(
                f"Profile '{resource_id}' does not exist.",
                subject="Profile Not Found",
                log_message=f"Profile '{resource_id}' not found for deletion",
            )

        # Don't allow deletion of 'default' profile without force
        if resource_id == "default" and not force:
            raise Abort(
                "Cannot delete 'default' profile without force=True.",
                subject="Cannot Delete Default Profile",
                log_message="Attempted to delete default profile without force",
            )

        try:
            self._delete_resource(resource_id)
            logger.info(f"Deleted profile '{resource_id}'")
            return True

        except Exception as e:
            logger.error(f"Failed to delete profile '{resource_id}': {str(e)}")
            raise Abort(
                f"Failed to delete profile '{resource_id}': {str(e)}",
                subject="Profile Deletion Failed",
                log_message=f"Profile deletion error: {str(e)}",
            )

    def get_all_profiles(self) -> Dict[str, Any]:
        """Get all profiles from the config file (public version of _load_all_resources)."""
        return self._load_all_resources()

    async def activate(
        self, ctx: typer.Context, profile_name: str, **kwargs: Any
    ) -> Dict[str, Any]:
        """Activate a profile.

        Args:
            ctx: Typer context
            profile_name: Name of profile to activate
            **kwargs: Additional parameters

        Returns:
            Profile activation result
        """
        existing_profiles = self._load_all_resources()

        if profile_name not in existing_profiles:
            raise Abort(
                f"Profile '{profile_name}' does not exist.",
                subject="Profile Not Found",
                log_message=f"Profile '{profile_name}' not found for activation",
            )

        try:
            set_active_profile(profile_name)
            logger.info(f"Set '{profile_name}' as active profile")

            return {
                "name": profile_name,
                "is_active": True,
                "message": f"Profile '{profile_name}' is now active",
            }

        except Exception as e:
            logger.error(f"Failed to activate profile '{profile_name}': {str(e)}")
            raise Abort(
                f"Failed to activate profile '{profile_name}': {str(e)}",
                subject="Profile Activation Failed",
                log_message=f"Profile activation error: {str(e)}",
            )


# Create a singleton instance for use in commands
profile_sdk = ProfileSDK()
