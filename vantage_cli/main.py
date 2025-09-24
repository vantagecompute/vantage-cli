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
"""Main typer app for vantage-cli."""

import datetime
import shutil
import subprocess
import sys
from typing import Optional

import typer
from jose import jwt
from loguru import logger
from rich import print_json
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from vantage_cli import AsyncTyper, __version__
from vantage_cli.auth import extract_persona, fetch_auth_tokens, is_token_expired
from vantage_cli.cache import clear_token_cache, load_tokens_from_cache, with_cache
from vantage_cli.client import attach_client
from vantage_cli.commands.alias import (
    apps_command,
    clouds_command,
    clusters_command,
    deployments_command,
    federations_command,
    networks_command,
    notebooks_command,
    profiles_command,
    teams_command,
)
from vantage_cli.commands.app import app_app
from vantage_cli.commands.cloud import cloud_app
from vantage_cli.commands.cluster import cluster_app
from vantage_cli.commands.config import config_app
from vantage_cli.commands.deployment import deployment_app
from vantage_cli.commands.license import license_app
from vantage_cli.commands.network import network_app
from vantage_cli.commands.notebook import notebook_app
from vantage_cli.commands.profile import profile_app
from vantage_cli.commands.storage import storage_app
from vantage_cli.config import (
    attach_settings,
    ensure_default_profile_exists,
    get_active_profile,
)
from vantage_cli.constants import VANTAGE_CLI_DEV_APPS_DIR
from vantage_cli.exceptions import handle_abort
from vantage_cli.schemas import CliContext, Persona, TokenSet

app = AsyncTyper(
    name="Vantage CLI",
    add_completion=False,
    help="Vantage Compute Command Line Interface",
    no_args_is_help=True,
    invoke_without_command=True,
)


@app.command()
@handle_abort
def version(ctx: typer.Context):
    """Show version and exit."""
    if hasattr(ctx.obj, "json_output") and ctx.obj and ctx.obj.json_output:
        import json

        print(json.dumps({"version": __version__}))
    else:
        typer.echo(__version__)


app.add_typer(app_app, name="app")
app.add_typer(cloud_app, name="cloud")
app.add_typer(cluster_app, name="cluster")
app.add_typer(config_app, name="config")
app.add_typer(license_app, name="license")
app.add_typer(network_app, name="network")
app.add_typer(notebook_app, name="notebook")
app.add_typer(profile_app, name="profile")
app.add_typer(storage_app, name="storage")
app.add_typer(deployment_app, name="deployment")


def setup_logging(verbose: bool = False):
    """Configure logging based on verbosity level."""
    logger.remove()

    if verbose:
        logger.add(sys.stdout, level="DEBUG")
        # Enable rich tracebacks only in verbose mode
        from rich import traceback

        traceback.install()
    else:
        # Disable rich tracebacks in normal mode
        # Reset exception handler to default
        sys.excepthook = sys.__excepthook__

    logger.debug("Logging initialized")


@app.callback(invoke_without_command=True)
@handle_abort
def main(ctx: typer.Context):
    """Handle global options for the application."""
    # If no subcommand is invoked, display help
    if ctx.invoked_subcommand is None:
        print(ctx.get_help())
        raise typer.Exit()

    ensure_default_profile_exists()

    # Get injected parameters from context object if they exist
    profile = getattr(ctx.obj, "profile", None) if hasattr(ctx, "obj") and ctx.obj else None
    verbose = getattr(ctx.obj, "verbose", False) if hasattr(ctx, "obj") and ctx.obj else False
    json_output = (
        getattr(ctx.obj, "json_output", False) if hasattr(ctx, "obj") and ctx.obj else False
    )

    # Use explicit profile if provided, otherwise get the active profile
    active_profile = profile if profile is not None else get_active_profile()

    setup_logging(verbose=verbose)

    # Create a single console instance for the entire application
    # console = Console(width=150)
    console = Console()

    cli_ctx = CliContext(
        profile=active_profile, verbose=verbose, json_output=json_output, console=console
    )
    ctx.obj = cli_ctx


@app.command(hidden=True)
@handle_abort
@with_cache
@attach_settings
async def dev_clear(ctx: typer.Context):
    """Clear the vantage-cli dev apps directory."""
    if VANTAGE_CLI_DEV_APPS_DIR.exists():
        shutil.rmtree(VANTAGE_CLI_DEV_APPS_DIR)
        ctx.obj.console.print(
            f"[green]Successfully cleared dev apps directory at {VANTAGE_CLI_DEV_APPS_DIR}[/green]"
        )


@app.command(hidden=True)
@handle_abort
@with_cache
@attach_settings
async def dev_init(ctx: typer.Context):
    """Initialize the vantage-cli dev apps directory by cloning from GitHub."""
    if clone_url := ctx.obj.settings.dev_apps_gh_url:
        if VANTAGE_CLI_DEV_APPS_DIR.exists():
            shutil.rmtree(VANTAGE_CLI_DEV_APPS_DIR)
        try:
            _ = subprocess.run(
                [
                    "git",
                    "clone",
                    clone_url,
                    str(VANTAGE_CLI_DEV_APPS_DIR),
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            ctx.obj.console.print(
                f"[green]Successfully cloned dev apps to {VANTAGE_CLI_DEV_APPS_DIR}[/green]"
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to clone dev apps: {e.stderr}")
            typer.echo(f"Error: Failed to clone repository - {e.stderr}", err=True)
            raise typer.Exit(1)
    else:
        typer.echo("Error: GH_PAT environment variable not found", err=True)
        raise typer.Exit(1)


def _check_existing_login(profile: str) -> Optional[str]:
    """Check if user is already logged in with a valid token.

    Returns:
        Email of logged in user if valid token exists, None otherwise
    """
    try:
        # Try to load tokens from cache
        token_set = load_tokens_from_cache(profile)

        # Check if access token is valid (not expired)
        if token_set.access_token and not is_token_expired(token_set.access_token):
            # Extract email from token for display
            try:
                persona = extract_persona(profile, token_set)
                return persona.identity_data.email
            except Exception as e:
                logger.debug(f"Could not extract persona from existing token: {e}")
                return None

    except Exception as e:
        # Token cache doesn't exist or other error - user not logged in
        logger.debug(f"No valid existing login found: {e}")
        return None

    return None


@app.command()
@handle_abort
@with_cache
@attach_settings
@attach_client
async def login(ctx: typer.Context):
    """Authenticate against the Vantage CLI by obtaining an authentication token."""
    # Check if user is already logged in with a valid token
    existing_email = _check_existing_login(ctx.obj.profile)
    if existing_email:
        console = ctx.obj.console
        console.print()
        console.print(
            Panel(
                f"Profile: [bold]{ctx.obj.profile}[/bold]\n\n"
                f"✅ Valid token already exists for user: [bold cyan]{existing_email}[/bold cyan]\n\n"
                f"If you want to generate a new token, please run '[bold magenta]vantage logout[/bold magenta]' first.",
                title="[green]Already Authenticated[/green]",
                border_style="green",
            )
        )
        console.print()
        return

    token_set: TokenSet = await fetch_auth_tokens(ctx.obj)
    persona: Persona = extract_persona(ctx.obj.profile, token_set)
    console = ctx.obj.console
    console.print()
    console.print(
        Panel(
            f"Profile: [bold]{ctx.obj.profile}[/bold]\n\n"
            f"✅ Successful authentication: [bold cyan]{persona.identity_data.email}[/bold cyan]\n\n"
            "You can now use the CLI to interact with Vantage Compute platform.",
            title="[green]Successful Authentication[/green]",
            border_style="green",
        )
    )
    console.print()


@app.command()
@handle_abort
@with_cache
async def logout(ctx: typer.Context):
    """Log out of the vantage-cli and clear saved user credentials."""
    existing_email = _check_existing_login(ctx.obj.profile)
    if existing_email:
        console = ctx.obj.console
        console.print()
        console.print(
            Panel(
                f"Profile: [bold]{ctx.obj.profile}[/bold]\n\n"
                f"✅ [bold]User:[/bold] {existing_email}\n\n"
                f"Please run '[bold magenta]vantage login[/bold magenta]' to log back in.",
                title="[green]Successfully Signed Out[/green]",
                border_style="green",
            )
        )
        console.print()
    clear_token_cache(ctx.obj.profile)


@app.command()
@handle_abort
@with_cache
@attach_settings
async def whoami(ctx: typer.Context):
    """Display information about the currently authenticated user."""
    # Get the JSON output preference from context
    json_output = getattr(ctx.obj, "json_output", False)

    try:
        # Extract persona from cached tokens
        persona: Persona = extract_persona(ctx.obj.profile)

        token_info = {}
        try:
            token_data = jwt.decode(
                persona.token_set.access_token,
                "",  # Empty key is acceptable when verify_signature is False
                options={
                    "verify_signature": False,
                    "verify_aud": False,
                    "verify_exp": False,  # Don't verify expiration for display
                },
            )

            # Extract additional fields if available
            if "exp" in token_data:
                exp_timestamp = token_data["exp"]
                exp_datetime = datetime.datetime.fromtimestamp(exp_timestamp)
                token_info["token_expires_at"] = exp_datetime.isoformat()
                token_info["token_expired"] = exp_datetime < datetime.datetime.now()

            if "iat" in token_data:
                iat_timestamp = token_data["iat"]
                iat_datetime = datetime.datetime.fromtimestamp(iat_timestamp)
                token_info["token_issued_at"] = iat_datetime.isoformat()

            if "sub" in token_data:
                token_info["user_id"] = token_data["sub"]

            if "name" in token_data:
                token_info["name"] = token_data["name"]

        except Exception as e:
            logger.debug(f"Could not decode token for additional info: {e}")

        # Prepare user information
        user_info = {
            "email": persona.identity_data.email,
            "client_id": persona.identity_data.client_id,
            "profile": ctx.obj.profile,
            "logged_in": True,
            **token_info,
        }

        if json_output:
            print_json(data=user_info)
        else:
            console = ctx.obj.console
            console.print()

            # Create a table for user information
            table = Table(
                title="Current User Information", show_header=True, header_style="bold white"
            )

            table.add_column("Property", style="bold cyan")
            table.add_column("Value", style="white")

            table.add_row("Email", user_info["email"] or "Not available")
            table.add_row("Client ID", user_info["client_id"])
            table.add_row("Profile", user_info["profile"])

            if "name" in user_info:
                table.add_row("Name", user_info["name"])

            if "user_id" in user_info:
                table.add_row("User ID", user_info["user_id"])

            if "token_issued_at" in user_info:
                table.add_row("Token Issued", user_info["token_issued_at"])

            if "token_expires_at" in user_info:
                exp_status = "❌ Expired" if user_info.get("token_expired", False) else "✅ Valid"
                table.add_row("Token Expires", f"{user_info['token_expires_at']} ({exp_status})")

            table.add_row("Status", "✅ Logged in")

            console.print(table)
            console.print()

    except Exception as e:
        logger.error(f"Failed to get user information: {str(e)}")

        error_info = {
            "logged_in": False,
            "error": "Not authenticated or token expired",
            "profile": ctx.obj.profile,
            "message": "Please run 'vantage login' to authenticate",
        }

        if json_output:
            print_json(data=error_info)
        else:
            console = ctx.obj.console
            console.print()
            console.print(
                Panel(
                    "❌ Not authenticated or token expired\n\n"
                    f"Current profile: [bold]{ctx.obj.profile}[/bold]\n"
                    f"Please run [bold]vantage login[/bold] to authenticate",
                    title="[red]Authentication Required[/red]",
                    border_style="red",
                )
            )
            console.print()


# Register alias commands
app.command("apps", hidden=True)(apps_command)
app.command("deployments", hidden=True)(deployments_command)
app.command("clouds", hidden=True)(clouds_command)
app.command("clusters", hidden=True)(clusters_command)
app.command("federations", hidden=True)(federations_command)
app.command("networks", hidden=True)(networks_command)
app.command("notebooks", hidden=True)(notebooks_command)
app.command("profiles", hidden=True)(profiles_command)
app.command("teams", hidden=True)(teams_command)


if __name__ == "__main__":
    app()
