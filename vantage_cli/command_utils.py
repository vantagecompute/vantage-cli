# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Command utilities for standardized option handling."""

import typer

from .command_base import get_effective_json_output


# Simple utility function for commands to check JSON output
def use_json(ctx: typer.Context) -> bool:
    """Check if JSON output should be used.

    This function checks both the global --json flag and any command-specific
    --json flag that was automatically injected by AsyncTyper.

    Args:
        ctx: The Typer context

    Returns:
        True if JSON output should be used, False otherwise

    Usage in commands:
        def my_command(ctx: typer.Context, name: str):
            if use_json(ctx):
                print('{"result": "success"}')
            else:
                print("Operation completed successfully")
    """
    # Check if AsyncTyper injected json_output into the context
    if ctx.obj and hasattr(ctx.obj, "json_output"):
        return ctx.obj.json_output

    # Fallback to the original method
    return get_effective_json_output(ctx, False)


# Alias for backward compatibility
should_use_json = use_json

# Export everything
__all__ = [
    "use_json",
    "should_use_json",
]
