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
"""Profile management CRUD operations for Vantage CLI."""

import logging

import typer
from typing_extensions import Annotated

from vantage_cli.exceptions import Abort, handle_abort
from vantage_cli.sdk.profile.crud import profile_sdk

logger = logging.getLogger(__name__)


@handle_abort
async def create_profile(
    ctx: typer.Context,
    profile_name: Annotated[str, typer.Argument(help="Name of the profile to create")],
    vantage_url: Annotated[
        str, typer.Option("--vantage-url", help="Vantage Platform URL")
    ] = "https://app.vantagecompute.ai",
    oidc_client_id: Annotated[str, typer.Option("--client-id", help="OIDC client ID")] = "default",
    oidc_max_poll_time: Annotated[
        int, typer.Option("--max-poll-time", help="OIDC max poll time in seconds")
    ] = 300,
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Overwrite existing profile")
    ] = False,
    activate: Annotated[
        bool, typer.Option("--activate", help="Activate this profile after creation")
    ] = False,
):
    """Create a new Vantage CLI profile."""
    # Use UniversalOutputFormatter for consistent output

    try:
        # Prepare settings
        from vantage_cli.config import Settings

        settings = Settings(
            vantage_url=vantage_url,
            oidc_max_poll_time=oidc_max_poll_time,
        )

        # Use SDK to create profile
        result = profile_sdk.create(
            name=profile_name,
            settings=settings,
            force=force,
            activate=activate,
        )

        # Use formatter to render the creation result
        ctx.obj.formatter.render_create(
            data=result.model_dump(),
            resource_name="Profile",
            success_message=f"Profile '{profile_name}' created successfully"
            + (" and set as active" if activate else ""),
        )

    except Abort:
        # SDK already handles Abort exceptions properly
        raise
    except Exception as e:
        logger.error(f"Failed to create profile '{profile_name}': {str(e)}")
        ctx.obj.formatter.render_error(
            error_message=f"Failed to create profile '{profile_name}': {str(e)}",
            details={"profile_name": profile_name},
        )


@handle_abort
async def delete_profile(
    ctx: typer.Context,
    profile_name: Annotated[str, typer.Argument(help="Name of the profile to delete")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation prompt")] = False,
):
    """Delete a Vantage CLI profile."""
    # Use UniversalOutputFormatter for consistent output

    # Confirmation prompt unless force is used
    if not force and not ctx.obj.json_output:
        from rich.prompt import Confirm

        ctx.obj.console.print(
            f"\n[yellow]⚠️  You are about to delete profile '[bold red]{profile_name}[/bold red]'[/yellow]"
        )
        ctx.obj.console.print(
            "[yellow]This will remove all settings and cached tokens for this profile![/yellow]"
        )

        if not Confirm.ask("Are you sure you want to proceed?"):
            ctx.obj.console.print("[dim]Deletion cancelled.[/dim]")
            return

    try:
        # Use SDK to delete profile
        success = profile_sdk.delete(profile_name, force=force)

        if success:
            # Use formatter to render the deletion result
            ctx.obj.formatter.render_delete(
                resource_name="Profile",
                resource_id=profile_name,
                success_message=f"Profile '{profile_name}' deleted successfully",
            )

    except Abort:
        # SDK already handles Abort exceptions properly
        raise
    except Exception as e:
        logger.error(f"Failed to delete profile '{profile_name}': {str(e)}")
        ctx.obj.formatter.render_error(
            error_message=f"Failed to delete profile '{profile_name}': {str(e)}",
            details={"profile_name": profile_name},
        )


@handle_abort
async def list_profiles(
    ctx: typer.Context,
):
    """List all Vantage CLI profiles."""
    # Use UniversalOutputFormatter for consistent output

    try:
        # Use the SDK to get profiles as Profile objects
        profiles = profile_sdk.list()

        if not profiles:
            ctx.obj.formatter.render_list(
                data=[], resource_name="Profiles", empty_message="No profiles found."
            )
            return

        # Convert Profile objects to dict format for the formatter
        profiles_data = []
        for profile in profiles:
            profile_dict = {
                "name": profile.name,
                "is_active": profile.is_active,  # Keep as boolean
                "vantage_url": profile.settings.vantage_url,
                "oidc_client_id": profile.settings.oidc_client_id or "default",
            }
            profiles_data.append(profile_dict)

        # Use formatter to render the profiles list
        ctx.obj.formatter.render_list(
            data=profiles_data, resource_name="Profiles", empty_message="No profiles found."
        )

    except Exception as e:
        logger.error(f"Failed to list profiles: {str(e)}")
        ctx.obj.formatter.render_error(error_message=f"Failed to list profiles: {str(e)}")


@handle_abort
async def get_profile(
    ctx: typer.Context,
    profile_name: Annotated[str, typer.Argument(help="Name of the profile to get")],
):
    """Get details of a specific Vantage CLI profile."""
    # Use UniversalOutputFormatter for consistent output

    try:
        # Use SDK to get profile
        profile = profile_sdk.get(profile_name)

        if profile is None:
            ctx.obj.formatter.render_error(
                error_message=f"Profile '{profile_name}' does not exist."
            )
            return

        # Convert Profile object to dict format for the formatter
        profile_data = {
            "name": profile.name,
            "is_active": profile.is_active,
            "vantage_url": profile.settings.vantage_url,
            "oidc_client_id": profile.settings.oidc_client_id or "default",
            "oidc_domain": profile.settings.oidc_domain,
            "oidc_max_poll_time": f"{profile.settings.oidc_max_poll_time} seconds",
            "api_base_url": profile.settings.get_apis_url(),
            "oidc_base_url": profile.settings.get_auth_url(),
            "tunnel_base_url": profile.settings.get_tunnel_url(),
        }

        # Use formatter to render the profile details
        ctx.obj.formatter.render_get(
            data=profile_data, resource_name="Profile", resource_id=profile_name
        )

    except Exception as e:
        logger.error(f"Failed to get profile '{profile_name}': {str(e)}")
        ctx.obj.formatter.render_error(
            error_message=f"Failed to get profile '{profile_name}': {str(e)}",
            details={"profile_name": profile_name},
        )


@handle_abort
async def use_profile(
    ctx: typer.Context,
    profile_name: Annotated[str, typer.Argument(help="Name of the profile to activate")],
):
    """Activate a profile for use in the current session."""
    # Use UniversalOutputFormatter for consistent output

    try:
        # Use SDK to activate profile
        result = profile_sdk.activate(profile_name)

        # Use formatter to render the activation result
        ctx.obj.formatter.render_update(
            data=result.model_dump(),
            resource_name="Profile",
            resource_id=profile_name,
            success_message=f"Profile '{profile_name}' is now active",
        )

    except Abort:
        # SDK already handles Abort exceptions properly
        raise
    except Exception as e:
        logger.error(f"Failed to activate profile '{profile_name}': {str(e)}")
        ctx.obj.formatter.render_error(
            error_message=f"Failed to activate profile '{profile_name}': {str(e)}",
            details={"profile_name": profile_name},
        )
