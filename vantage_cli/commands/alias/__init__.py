"""Alias commands for vantage CLI."""

from .apps import apps_command
from .clouds import clouds_command
from .clusters import clusters_command
from .federations import federations_command
from .networks import networks_command
from .notebooks import notebooks_command
from .profiles import profiles_command
from .teams import teams_command

__all__ = [
    "apps_command",
    "clouds_command",
    "clusters_command",
    "federations_command",
    "networks_command",
    "notebooks_command",
    "profiles_command",
    "teams_command",
]
