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
"""Configuration management commands for Vantage CLI."""

from vantage_cli import AsyncTyper

from .clear import clear_config

# Create the config app
config_app = AsyncTyper(
    name="config",
    help="Manage Vantage CLI configuration and settings.",
    invoke_without_command=True,
    no_args_is_help=True,
)

# Register subcommands
config_app.command("clear")(clear_config)
