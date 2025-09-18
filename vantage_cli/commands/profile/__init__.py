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
"""Profile management commands for Vantage CLI."""

import typer

from .crud import create_profile, delete_profile, get_profile, list_profiles, use_profile

# Create the profile app
profile_app = typer.Typer(
    name="profile",
    help="Manage Vantage CLI profiles to work with different environments and configurations.",
    invoke_without_command=True,
    no_args_is_help=True,
)

# Register subcommands
profile_app.command("create")(create_profile)
profile_app.command("delete")(delete_profile)
profile_app.command("get")(get_profile)
profile_app.command("list")(list_profiles)
profile_app.command("use")(use_profile)
