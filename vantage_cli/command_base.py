# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Base command utilities for consistent global option handling."""

from typing import Optional

import typer
from typing_extensions import Annotated

# Reusable type annotations for global options
JsonOption = Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")]
VerboseOption = Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")]


class GlobalOptions:
    """Helper class to manage global options consistently across commands."""

    def __init__(self, ctx: typer.Context, local_json: bool = False, local_verbose: bool = False):
        self.ctx = ctx
        self.local_json = local_json
        self.local_verbose = local_verbose

    @property
    def json_output(self) -> bool:
        """Get effective JSON output setting."""
        global_json = getattr(self.ctx.obj, "json_output", False) if self.ctx.obj else False
        return self.local_json or global_json

    @property
    def verbose(self) -> bool:
        """Get effective verbose setting."""
        global_verbose = getattr(self.ctx.obj, "verbose", False) if self.ctx.obj else False
        return self.local_verbose or global_verbose

    @property
    def profile(self) -> Optional[str]:
        """Get the active profile."""
        return getattr(self.ctx.obj, "profile", None) if self.ctx.obj else None


def get_global_options(
    ctx: typer.Context, json_output: bool = False, verbose: bool = False
) -> GlobalOptions:
    """Create GlobalOptions instance."""
    return GlobalOptions(ctx, json_output, verbose)


# Utility functions for individual options
def get_effective_json_output(ctx: typer.Context, local_json: bool = False) -> bool:
    """Get the effective JSON output setting with precedence: local > global > default."""
    global_json = getattr(ctx.obj, "json_output", False) if ctx.obj else False
    return local_json or global_json


def get_effective_verbose(ctx: typer.Context, local_verbose: bool = False) -> bool:
    """Get the effective verbose setting with precedence: local > global > default."""
    global_verbose = getattr(ctx.obj, "verbose", False) if ctx.obj else False
    return local_verbose or global_verbose


def get_active_profile(ctx: typer.Context) -> Optional[str]:
    """Get the active profile from context."""
    return getattr(ctx.obj, "profile", None) if ctx.obj else None
