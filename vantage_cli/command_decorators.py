# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Enhanced command decorators for consistent option handling."""

import functools
import inspect
from typing import Callable, Optional

import typer
from typing_extensions import Annotated

from .command_base import get_effective_json_output

# Standard JSON option that can be used across all commands
JsonOption = Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")]


def with_json_option(func: Callable) -> Callable:
    """Add a json_output parameter to any command function automatically.

    This decorator modifies the function signature to include the --json option,
    so you don't need to manually add `json_output: JsonOption = False` to every command.

    Usage:
        @app.command()
        @with_json_option
        def my_command(ctx: typer.Context, name: str, json_output: bool = False):
            use_json = should_use_json(ctx, json_output)
            # ... command logic

    Or with async functions:
        @app.command()
        @with_json_option
        async def my_async_command(ctx: typer.Context, name: str, json_output: bool = False):
            use_json = should_use_json(ctx, json_output)
            # ... command logic
    """
    # Get the original function signature
    sig = inspect.signature(func)
    params = list(sig.parameters.values())

    # Check if json_output parameter already exists
    if "json_output" not in sig.parameters:
        # Add json_output parameter at the end
        json_param = inspect.Parameter(
            "json_output", inspect.Parameter.KEYWORD_ONLY, default=False, annotation=JsonOption
        )
        params.append(json_param)

        # Create new signature with the json_output parameter
        new_sig = sig.replace(parameters=params)

        # Create wrapper function that accepts the json_output parameter
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        # Apply the new signature to the wrapper
        wrapper.__signature__ = new_sig  # type: ignore[misc]

        return wrapper
    else:
        # Function already has json_output parameter, return as-is
        return func


def should_use_json(ctx: typer.Context, local_json: bool = False) -> bool:
    """Determine if JSON output should be used based on context and local flag.

    This function checks both the global --json flag passed to the main command
    and any local --json flag passed to the subcommand.

    Args:
        ctx: The Typer context
        local_json: Local JSON flag from the command

    Returns:
        True if JSON output should be used, False otherwise
    """
    return get_effective_json_output(ctx, local_json)


def app_command(app: typer.Typer, name: Optional[str] = None, auto_json: bool = True, **kwargs):
    """Enhanced command decorator that optionally auto-injects the --json option.

    This is a convenience function that combines the standard command decorator
    with the with_json_option decorator.

    Args:
        app: The Typer app instance
        name: Command name
        auto_json: Whether to automatically add the --json option
        **kwargs: Additional arguments passed to the command decorator

    Usage:
        @app_command(app)
        def my_command(ctx: typer.Context, name: str, json_output: bool = False):
            use_json = should_use_json(ctx, json_output)
            # ... command logic
    """

    def decorator(func: Callable) -> Callable:
        # Apply json option decorator if requested
        if auto_json:
            func = with_json_option(func)

        # Apply the standard command decorator
        return app.command(name=name, **kwargs)(func)

    return decorator
