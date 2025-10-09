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
"""Organizations management SDK functions.

This module provides SDK functions for organization-level administrative operations
such as managing extra attributes and other organization configurations.
"""

from typing import Any, Dict, Optional

import typer


async def get_extra_attributes(ctx: typer.Context) -> Optional[Dict[Any, Any]]:
    """Get organization extra attributes.

    This function retrieves the list of extra attributes configured for the organization.
    Extra attributes are custom fields that can be added to various entities.

    The REST client is automatically initialized and attached to ctx.obj.rest_client
    by the @attach_vantage_rest_client decorator.

    Args:
        ctx: Typer context with rest_client, settings, and persona already attached

    Returns:
        List of extra attribute dictionaries containing attribute definitions

    Raises:
        httpx.HTTPStatusError: If the API request fails
        Exception: For other request failures

    Example:
        >>> import typer
        >>> ctx = typer.Context(...)  # Context with settings and persona
        >>> attributes = await get_extra_attributes(ctx)
        >>> print(attributes)
    """
    path = "/admin/management/organizations/extra-attributes"
    try:
        response = await ctx.obj.rest_client.get(path)
    except Exception as _:
        return None

    if response.status_code == 200:
        return response.json()
    return None
