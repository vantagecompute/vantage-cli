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
"""Profile CRUD SDK for managing Vantage CLI profiles."""

import logging
from typing import Dict, List, Optional

from vantage_cli.cache import clear_token_cache
from vantage_cli.config import (
    Settings,
    get_active_profile,
    init_user_filesystem,
    set_active_profile,
)
from vantage_cli.constants import USER_TOKEN_CACHE_DIR
from vantage_cli.exceptions import Abort
from vantage_cli.sdk.profile.schema import Profile, load_profiles

logger = logging.getLogger(__name__)


class ProfileSDK:
    """SDK for profile CRUD operations.

    This SDK provides operations for managing Vantage CLI profiles,
    which contain settings for connecting to Vantage API instances.
    Profiles are persisted to ~/.vantage-cli/profiles.json.
    """

    def __init__(self):
        """Initialize the Profile SDK."""
        self._profiles: Dict[str, Profile] = {}
        self._load_from_file()
        logger.debug("Initialized ProfileSDK")

    def _load_from_file(self):
        """Load profiles from the JSON file."""
        profiles_data = load_profiles()
        active_profile_name = get_active_profile()

        for profile_name, settings_data in profiles_data.items():
            try:
                settings = Settings(**settings_data)
                profile = Profile(
                    name=profile_name,
                    settings=settings,
                    is_active=(profile_name == active_profile_name),
                )
                self._profiles[profile_name] = profile
            except Exception as e:
                logger.warning(f"Failed to load profile '{profile_name}': {e}")

        logger.debug(f"Loaded {len(self._profiles)} profiles from file")

    def _clear_profile_token_cache(self, profile_name: str) -> None:
        """Clear cached tokens for a profile."""
        try:
            clear_token_cache(profile_name)
        except Exception as e:
            logger.warning(f"Failed to clear token cache for profile '{profile_name}': {e}")

        # Remove profile token cache directory if it exists
        profile_cache_dir = USER_TOKEN_CACHE_DIR / profile_name
        if profile_cache_dir.exists():
            import shutil

            shutil.rmtree(profile_cache_dir)

    def create(
        self,
        name: str,
        settings: Settings,
        activate: bool = False,
        force: bool = False,
    ) -> Profile:
        """Create a new profile.

        Args:
            name: Profile name
            settings: Profile settings
            activate: Set as active profile
            force: Overwrite existing profile

        Returns:
            Created Profile instance

        Raises:
            Abort: If profile exists and force is False
        """
        # Check if profile already exists
        if name in self._profiles and not force:
            raise Abort(
                f"Profile '{name}' already exists. Use force=True to overwrite.",
                subject="Profile Exists",
                log_message=f"Profile '{name}' already exists",
            )

        try:
            # Initialize filesystem for this profile
            init_user_filesystem(name)

            # Create profile object
            profile = Profile(
                name=name,
                settings=settings,
                is_active=activate,
            )

            # Save the profile
            profile.write()

            # Store in memory
            self._profiles[name] = profile

            # Set as active profile if requested
            if activate:
                set_active_profile(name)
                # Update is_active for all profiles
                for prof in self._profiles.values():
                    prof.is_active = prof.name == name
                logger.info(f"Set '{name}' as active profile")

            logger.info(f"Created profile '{name}'")
            return profile

        except Exception as e:
            logger.error(f"Failed to create profile '{name}': {str(e)}")
            raise Abort(
                f"Failed to create profile '{name}': {str(e)}",
                subject="Profile Creation Failed",
                log_message=f"Profile creation error: {str(e)}",
            )

    def get(self, profile_name: str) -> Optional[Profile]:
        """Get a specific profile.

        Args:
            profile_name: Name of the profile

        Returns:
            Profile instance or None if not found
        """
        return self._profiles.get(profile_name)

    def list(self) -> List[Profile]:
        """List all profiles.

        Returns:
            List of Profile instances
        """
        return list(self._profiles.values())

    def update(
        self,
        profile_name: str,
        settings: Optional[Settings] = None,
    ) -> Optional[Profile]:
        """Update an existing profile.

        Args:
            profile_name: Name of the profile to update
            settings: New settings (optional)

        Returns:
            Updated Profile instance or None if not found

        Raises:
            Abort: If profile doesn't exist
        """
        profile = self._profiles.get(profile_name)
        if not profile:
            raise Abort(
                f"Profile '{profile_name}' does not exist.",
                subject="Profile Not Found",
                log_message=f"Profile '{profile_name}' not found for update",
            )

        try:
            if settings is not None:
                profile.settings = settings

            profile.write()
            logger.info(f"Updated profile '{profile_name}'")
            return profile

        except Exception as e:
            logger.error(f"Failed to update profile '{profile_name}': {str(e)}")
            raise Abort(
                f"Failed to update profile '{profile_name}': {str(e)}",
                subject="Profile Update Failed",
                log_message=f"Profile update error: {str(e)}",
            )

    def delete(self, profile_name: str, force: bool = False) -> bool:
        """Delete a profile.

        Args:
            profile_name: Name of the profile to delete
            force: Allow deletion of 'default' profile

        Returns:
            True if deletion was successful

        Raises:
            Abort: If profile doesn't exist or is default without force
        """
        if profile_name not in self._profiles:
            raise Abort(
                f"Profile '{profile_name}' does not exist.",
                subject="Profile Not Found",
                log_message=f"Profile '{profile_name}' not found for deletion",
            )

        # Don't allow deletion of 'default' profile without force
        if profile_name == "default" and not force:
            raise Abort(
                "Cannot delete 'default' profile without force=True.",
                subject="Cannot Delete Default Profile",
                log_message="Attempted to delete default profile without force",
            )

        try:
            # Remove from memory
            del self._profiles[profile_name]

            # Remove from file
            from vantage_cli.sdk.profile.schema import load_profiles, save_profiles

            profiles_data = load_profiles()
            if profile_name in profiles_data:
                del profiles_data[profile_name]
                save_profiles(profiles_data)

            # Clear token cache
            self._clear_profile_token_cache(profile_name)

            logger.info(f"Deleted profile '{profile_name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to delete profile '{profile_name}': {str(e)}")
            raise Abort(
                f"Failed to delete profile '{profile_name}': {str(e)}",
                subject="Profile Deletion Failed",
                log_message=f"Profile deletion error: {str(e)}",
            )

    def activate(self, profile_name: str) -> Profile:
        """Activate a profile.

        Args:
            profile_name: Name of profile to activate

        Returns:
            Activated Profile instance

        Raises:
            Abort: If profile doesn't exist
        """
        if profile_name not in self._profiles:
            raise Abort(
                f"Profile '{profile_name}' does not exist.",
                subject="Profile Not Found",
                log_message=f"Profile '{profile_name}' not found for activation",
            )

        try:
            set_active_profile(profile_name)

            # Update is_active for all profiles
            for prof in self._profiles.values():
                prof.is_active = prof.name == profile_name

            logger.info(f"Set '{profile_name}' as active profile")
            return self._profiles[profile_name]

        except Exception as e:
            logger.error(f"Failed to activate profile '{profile_name}': {str(e)}")
            raise Abort(
                f"Failed to activate profile '{profile_name}': {str(e)}",
                subject="Profile Activation Failed",
                log_message=f"Profile activation error: {str(e)}",
            )


# Create singleton instance
profile_sdk = ProfileSDK()


__all__ = [
    "ProfileSDK",
    "profile_sdk",
]
