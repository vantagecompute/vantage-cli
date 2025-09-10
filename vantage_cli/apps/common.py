# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Common validation utilities for deployment apps."""

from typing import Any, Dict, Optional

import typer
from rich.console import Console

from vantage_cli.constants import (
    ERROR_NO_CLIENT_ID,
    ERROR_NO_CLIENT_SECRET,
    ERROR_NO_CLUSTER_DATA,
)


def validate_cluster_data(
    cluster_data: Optional[Dict[str, Any]], console: Console
) -> Dict[str, Any]:
    """Validate that cluster data exists and contains required fields.

    Args:
        cluster_data: Optional cluster configuration dictionary
        console: Rich console for error output

    Returns:
        Validated cluster data dictionary

    Raises:
        typer.Exit: If validation fails
    """
    if not cluster_data:
        console.print(ERROR_NO_CLUSTER_DATA)
        raise typer.Exit(code=1)
    return cluster_data


def validate_client_credentials(
    cluster_data: Dict[str, Any], console: Console
) -> tuple[str, Optional[str]]:
    """Validate and extract client credentials from cluster data.

    Args:
        cluster_data: Cluster configuration dictionary
        console: Rich console for error output

    Returns:
        Tuple of (client_id, client_secret) where client_secret may be None

    Raises:
        typer.Exit: If client_id is missing
    """
    client_id = cluster_data.get("clientId", None)
    if not client_id:
        console.print(ERROR_NO_CLIENT_ID)
        raise typer.Exit(code=1)

    client_secret = cluster_data.get("clientSecret", None)
    return client_id, client_secret


def require_client_secret(client_secret: Optional[str], console: Console) -> str:
    """Validate that client secret exists.

    Args:
        client_secret: Optional client secret string
        console: Rich console for error output

    Returns:
        Validated client secret string

    Raises:
        typer.Exit: If client secret is missing
    """
    if not client_secret:
        console.print(ERROR_NO_CLIENT_SECRET)
        raise typer.Exit(code=1)
    return client_secret
