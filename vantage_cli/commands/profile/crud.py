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

import json
from typing import Any, Dict

import typer
from loguru import logger
from rich import print_json
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from typing_extensions import Annotated

from vantage_cli.config import (
    Settings,
    dump_settings,
    get_active_profile,
    init_user_filesystem,
    set_active_profile,
)
from vantage_cli.constants import USER_CONFIG_FILE, USER_TOKEN_CACHE_DIR
from vantage_cli.exceptions import Abort, handle_abort
from vantage_cli.render import RenderStepOutput


@handle_abort
async def create_profile(
    ctx: typer.Context,
    command_start_time: float,
    profile_name: Annotated[str, typer.Argument(help="Name of the profile to create")],
    api_base_url: Annotated[
        str, typer.Option("--api-url", help="API base URL")
    ] = "https://apis.vantagecompute.ai",
    tunnel_api_url: Annotated[
        str, typer.Option("--tunnel-url", help="Tunnel API URL")
    ] = "https://tunnel.vantagecompute.ai",
    oidc_base_url: Annotated[
        str, typer.Option("--oidc-url", help="OIDC base URL")
    ] = "https://auth.vantagecompute.ai",
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
    json_output: Annotated[
        bool, typer.Option("--json", "-j", help="Output in JSON format")
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose terminal output")
    ] = False,
):
    """Create a new Vantage CLI profile."""
    # Use the json_output parameter directly
    effective_json = json_output

    # Check for JSON bypass early
    if effective_json:
        # For JSON output, we bypass the progress rendering entirely and handle in-line
        pass

    renderer = RenderStepOutput(
        console=ctx.obj.console,
        operation_name=f"Create Profile '{profile_name}'",
        step_names=["Validating parameters", "Creating profile", "Configuring settings"],
        verbose=verbose,
        command_start_time=command_start_time,
    )

    with renderer:
        # Check if profile already exists
        existing_profiles = _get_all_profiles()

        if profile_name in existing_profiles and not force:
            message = f"Profile '{profile_name}' already exists. Use --force to overwrite."
            if effective_json:
                result = {"success": False, "profile_name": profile_name, "message": message}
                print_json(data=result)
                return
            else:
                raise Abort(
                    message,
                    subject="Profile Exists",
                    log_message=f"Profile '{profile_name}' already exists",
                )

        renderer.complete_step("Validating parameters")

        # Create the settings
        try:
            settings = Settings(
                api_base_url=api_base_url,
                oidc_base_url=oidc_base_url,
                tunnel_api_url=tunnel_api_url,
                oidc_client_id=oidc_client_id,
                oidc_max_poll_time=oidc_max_poll_time,
            )

            renderer.complete_step("Creating profile")

            # Initialize filesystem for this profile
            init_user_filesystem(profile_name)

            # Save the settings
            dump_settings(profile_name, settings)

            # Set as active profile if requested
            if activate:
                set_active_profile(profile_name)
                logger.info(f"Set '{profile_name}' as active profile")

            renderer.complete_step("Configuring settings")

            logger.info(f"Created profile '{profile_name}'")

            if effective_json:
                result = {
                    "success": True,
                    "profile_name": profile_name,
                    "settings": settings.model_dump(),
                    "is_active": activate,
                    "message": f"Profile '{profile_name}' created successfully",
                }
                if activate:
                    result["message"] += " and set as active"
                print_json(data=result)
            else:
                ctx.obj.console.print()
                message = (
                    f"✅ Profile '[bold cyan]{profile_name}[/bold cyan]' created successfully!"
                )
                if activate:
                    message += "\n🎯 Set as active profile!"
                ctx.obj.console.print(
                    Panel(message, title="[green]Profile Created[/green]", border_style="green")
                )

                # Show profile details
                _render_profile_details(profile_name, settings, ctx.obj.console)

        except Exception as e:
            logger.error(f"Failed to create profile '{profile_name}': {str(e)}")
            if effective_json:
                result = {
                    "success": False,
                    "profile_name": profile_name,
                    "message": f"Failed to create profile: {str(e)}",
                }
                print_json(data=result)
            else:
                raise Abort(
                    f"Failed to create profile '{profile_name}': {str(e)}",
                    subject="Profile Creation Failed",
                    log_message=f"Profile creation error: {str(e)}",
                )


@handle_abort
def delete_profile(
    ctx: typer.Context,
    profile_name: Annotated[str, typer.Argument(help="Name of the profile to delete")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation prompt")] = False,
    json_output: Annotated[
        bool, typer.Option("--json", "-j", help="Output in JSON format")
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose terminal output")
    ] = False,
):
    """Delete a Vantage CLI profile."""
    # Use the json_output parameter directly
    effective_json = json_output

    # Check if profile exists
    existing_profiles = _get_all_profiles()

    if profile_name not in existing_profiles:
        message = f"Profile '{profile_name}' does not exist."
        if effective_json:
            result = {"success": False, "profile_name": profile_name, "message": message}
            print_json(data=result)
            return
        else:
            raise Abort(
                message,
                subject="Profile Not Found",
                log_message=f"Profile '{profile_name}' not found for deletion",
            )

    # Don't allow deletion of 'default' profile without force
    if profile_name == "default" and not force:
        message = "Cannot delete 'default' profile without --force flag."
        if effective_json:
            result = {"success": False, "profile_name": profile_name, "message": message}
            print_json(data=result)
            return
        else:
            raise Abort(
                message,
                subject="Cannot Delete Default Profile",
                log_message="Attempted to delete default profile without force",
            )

    # Confirmation prompt unless force is used
    if not force and not effective_json:
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
        # Remove from config file
        if USER_CONFIG_FILE.exists():
            all_profiles = json.loads(USER_CONFIG_FILE.read_text())
            if profile_name in all_profiles:
                del all_profiles[profile_name]
                USER_CONFIG_FILE.write_text(json.dumps(all_profiles, indent=2))

        # Clear token cache for this profile
        _clear_profile_token_cache(profile_name)

        # Remove profile token cache directory if it exists
        profile_cache_dir = USER_TOKEN_CACHE_DIR / profile_name
        if profile_cache_dir.exists():
            import shutil

            shutil.rmtree(profile_cache_dir)

        logger.info(f"Deleted profile '{profile_name}'")

        if effective_json:
            result = {
                "success": True,
                "profile_name": profile_name,
                "message": f"Profile '{profile_name}' deleted successfully",
            }
            print_json(data=result)
        else:
            ctx.obj.console.print()
            ctx.obj.console.print(
                Panel(
                    f"✅ Profile '[bold cyan]{profile_name}[/bold cyan]' deleted successfully!",
                    title="[green]Profile Deleted[/green]",
                    border_style="green",
                )
            )
            ctx.obj.console.print()

    except Exception as e:
        logger.error(f"Failed to delete profile '{profile_name}': {str(e)}")
        if effective_json:
            result = {
                "success": False,
                "profile_name": profile_name,
                "message": f"Failed to delete profile: {str(e)}",
            }
            print_json(data=result)
        else:
            raise Abort(
                f"Failed to delete profile '{profile_name}': {str(e)}",
                subject="Profile Deletion Failed",
                log_message=f"Profile deletion error: {str(e)}",
            )


@handle_abort
def get_profile(
    ctx: typer.Context,
    profile_name: Annotated[str, typer.Argument(help="Name of the profile to get details for")],
    json_output: Annotated[
        bool, typer.Option("--json", "-j", help="Output in JSON format")
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose terminal output")
    ] = False,
):
    """Get details of a specific Vantage CLI profile."""
    # Use the json_output parameter directly
    effective_json = json_output

    # Check if profile exists
    existing_profiles = _get_all_profiles()

    if profile_name not in existing_profiles:
        message = f"Profile '{profile_name}' does not exist."
        if effective_json:
            result = {"success": False, "profile_name": profile_name, "message": message}
            print_json(data=result)
            return
        else:
            raise Abort(
                message,
                subject="Profile Not Found",
                log_message=f"Profile '{profile_name}' not found",
            )

    try:
        # Load the profile settings
        profile_data = existing_profiles[profile_name]
        settings = Settings(**profile_data)

        if effective_json:
            result = {
                "success": True,
                "profile_name": profile_name,
                "settings": settings.model_dump(),
            }
            print_json(data=result)
        else:
            _render_profile_details(profile_name, settings, ctx.obj.console)

    except Exception as e:
        logger.error(f"Failed to get profile '{profile_name}': {str(e)}")
        if effective_json:
            result = {
                "success": False,
                "profile_name": profile_name,
                "message": f"Failed to get profile: {str(e)}",
            }
            print_json(data=result)
        else:
            raise Abort(
                f"Failed to get profile '{profile_name}': {str(e)}",
                subject="Profile Retrieval Failed",
                log_message=f"Profile retrieval error: {str(e)}",
            )


@handle_abort
def list_profiles(
    ctx: typer.Context,
    json_output: Annotated[
        bool, typer.Option("--json", "-j", help="Output in JSON format")
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose terminal output")
    ] = False,
):
    """List all Vantage CLI profiles."""
    # Use the json_output parameter directly
    effective_json = json_output

    try:
        # Get active profile from file system
        active_profile = get_active_profile()

        # Get all profiles
        all_profiles = _get_all_profiles()

        if not all_profiles:
            if effective_json:
                from vantage_cli.render import render_json

                render_json({"profiles": [], "total": 0, "current_profile": active_profile})
            else:
                ctx.obj.console.print()
                ctx.obj.console.print(Panel("No profiles found.", title="[yellow]No Profiles"))
                ctx.obj.console.print()
            return

        if effective_json:
            # JSON output - bypass progress system entirely
            profiles_list = []
            for name, settings_data in all_profiles.items():
                profile_info = {
                    "name": name,
                    "settings": settings_data,
                    "is_current": name == active_profile,
                }
                profiles_list.append(profile_info)

            result = {
                "profiles": profiles_list,
                "total": len(profiles_list),
                "current_profile": active_profile,
            }
            from vantage_cli.render import render_json

            render_json(result)
            return

        # Rich output with progress system
        command_start_time = getattr(ctx.obj, "command_start_time", None) if ctx.obj else None
        renderer = RenderStepOutput(
            console=ctx.obj.console,
            operation_name="List Profiles",
            step_names=["Loading profiles", "Formatting output"],
            verbose=verbose,
            command_start_time=command_start_time,
        )

        with renderer:
            # Step 1: Loading (already done)
            renderer.complete_step("Loading profiles")

            # Step 2: Format and display output
            renderer.start_step("Formatting output")

            _render_profiles_table(all_profiles, active_profile, ctx.obj.console)

            renderer.complete_step("Formatting output")

    except Exception as e:
        logger.error(f"Failed to list profiles: {str(e)}")
        if effective_json:
            from vantage_cli.render import render_json

            result = {"success": False, "message": f"Failed to list profiles: {str(e)}"}
            render_json(result)
        else:
            raise Abort(
                f"Failed to list profiles: {str(e)}",
                subject="Profile Listing Failed",
                log_message=f"Profile listing error: {str(e)}",
            )


@handle_abort
def use_profile(
    ctx: typer.Context,
    profile_name: Annotated[str, typer.Argument(help="Name of the profile to activate")],
    json_output: Annotated[
        bool, typer.Option("--json", "-j", help="Output in JSON format")
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose terminal output")
    ] = False,
):
    """Activate a profile for use in the current session."""
    # Use the json_output parameter directly
    effective_json = json_output

    # Check if profile exists
    existing_profiles = _get_all_profiles()

    if profile_name not in existing_profiles:
        message = f"Profile '{profile_name}' does not exist."
        if effective_json:
            result = {
                "success": False,
                "profile_name": profile_name,
                "message": message,
                "available_profiles": list(existing_profiles.keys()),
            }
            print_json(data=result)
            return
        else:
            ctx.obj.console.print()
            ctx.obj.console.print(
                Panel(
                    f"❌ Profile '[bold red]{profile_name}[/bold red]' does not exist.\n\n"
                    f"Available profiles: {', '.join(existing_profiles.keys()) if existing_profiles else 'None'}",
                    title="[red]Profile Not Found[/red]",
                    border_style="red",
                )
            )
            raise typer.Exit(1)

    # Set as active profile
    try:
        set_active_profile(profile_name)
        logger.info(f"Set '{profile_name}' as active profile")

        if effective_json:
            result = {
                "success": True,
                "profile_name": profile_name,
                "message": f"Profile '{profile_name}' is now active",
                "note": "This profile will be used for all future commands until changed",
            }
            print_json(data=result)
        else:
            ctx.obj.console.print()
            ctx.obj.console.print(
                Panel(
                    f"🎯 Profile '[bold cyan]{profile_name}[/bold cyan]' is now active!\n\n"
                    f"This profile will be used for all future commands until changed.",
                    title="[green]Profile Activated[/green]",
                    border_style="green",
                )
            )

    except Exception as e:
        logger.error(f"Failed to set '{profile_name}' as active: {str(e)}")
        if effective_json:
            result = {
                "success": False,
                "profile_name": profile_name,
                "message": f"Failed to activate profile: {str(e)}",
            }
            print_json(data=result)
        else:
            raise Abort(
                f"Failed to activate profile '{profile_name}': {str(e)}",
                subject="Profile Activation Failed",
                log_message=f"Profile activation error: {str(e)}",
            )


def _get_all_profiles() -> Dict[str, Any]:
    """Get all profiles from the config file."""
    if not USER_CONFIG_FILE.exists():
        return {}

    try:
        return json.loads(USER_CONFIG_FILE.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def _render_profiles_table(
    profiles: Dict[str, Any], current_profile: str, console: Console
) -> None:
    """Render a table of all profiles."""
    # Create the table
    table = Table(
        title="Vantage CLI Profiles",
        caption=f"Items: {len(profiles)} • Current profile: [bold]{current_profile}[/bold]",
        show_header=True,
        header_style="bold white",
    )

    # Add columns
    table.add_column("Name", style="bold cyan")
    table.add_column("Current", style="green", justify="center")
    table.add_column("API Base URL", style="blue")
    table.add_column("OIDC Base URL", style="yellow")
    table.add_column("Tunnel API URL", style="yellow")
    table.add_column("Client ID", style="white")

    # Add rows
    for name, settings_data in profiles.items():
        current_marker = "✓" if name == current_profile else ""

        # Handle both old and new settings format
        api_url = settings_data.get("api_base_url", "N/A")
        oidc_url = settings_data.get("oidc_base_url", "N/A")
        tunnel_url = settings_data.get("tunnel_api_url", "N/A")
        client_id = settings_data.get("oidc_client_id", "N/A")

        table.add_row(
            name, current_marker, str(api_url), str(oidc_url), str(tunnel_url), str(client_id)
        )

    console.print()
    console.print(table)
    console.print()


def _render_profile_details(profile_name: str, settings: Settings, console: Console) -> None:
    """Render detailed information for a single profile."""
    # Create a table matching the whoami command style
    table = Table(
        title=f"Profile Details: {profile_name}", show_header=True, header_style="bold white"
    )

    table.add_column("Property", style="bold cyan")
    table.add_column("Value", style="white")

    # Add profile information
    table.add_row("Profile Name", profile_name)
    table.add_row("API Base URL", settings.api_base_url)
    table.add_row("OIDC Base URL", settings.oidc_base_url)
    table.add_row("Tunnel Base URL", settings.tunnel_api_url)
    table.add_row("OIDC Domain", settings.oidc_domain)
    table.add_row("OIDC Client ID", settings.oidc_client_id)
    table.add_row("OIDC Max Poll Time", f"{settings.oidc_max_poll_time} seconds")
    table.add_row("Supported Clouds", ", ".join(settings.supported_clouds))

    console.print()
    console.print(table)
    console.print()


def _clear_profile_token_cache(profile: str) -> None:
    """Clear token cache for a specific profile."""
    token_dir = USER_TOKEN_CACHE_DIR / profile
    if token_dir.exists():
        access_token_path = token_dir / "access.token"
        refresh_token_path = token_dir / "refresh.token"

        logger.debug(f"Removing access token at {access_token_path}")
        if access_token_path.exists():
            access_token_path.unlink()

        logger.debug(f"Removing refresh token at {refresh_token_path}")
        if refresh_token_path.exists():
            refresh_token_path.unlink()
