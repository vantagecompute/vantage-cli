# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Simplified command helpers to avoid repeating JSON options."""

import typer
from typing_extensions import Annotated

# Standard JSON option type
JsonOption = Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")]


def simple_command(app: typer.Typer, name: str | None = None):
    """Wrap app.command() and provide a consistent pattern.

    Usage:
        @simple_command(clouds_app, "list")
        def list_clouds(ctx: typer.Context, json_output: JsonOption = False):
            use_json = should_use_json(ctx, json_output)
            # ... command implementation
    """

    def decorator(func):
        return app.command(name)(func)

    return decorator


# Alternative: Create a base function that handles common patterns
def make_json_command(app: typer.Typer, name: str, func, help_text: str | None = None):
    """Register a command with automatic JSON handling.

    This function takes a command implementation and automatically registers it
    with the JSON option handling. The command function should accept:
    - ctx: typer.Context
    - Any other parameters
    - json_output: bool (will be added automatically)

    Usage:
        def my_command_impl(ctx, json_output=False):
            use_json = should_use_json(ctx, json_output)
            # ... implementation

        make_json_command(clouds_app, "list", my_command_impl, "List all clouds")
    """

    # Create wrapper with proper signature
    def command_wrapper(ctx: typer.Context, json_output: JsonOption = False, **kwargs):
        return func(ctx, json_output=json_output, **kwargs)

    # Set help text if provided
    if help_text:
        command_wrapper.__doc__ = help_text

    # Register the command
    return app.command(name)(command_wrapper)


# For new commands, you can use this pattern:
def create_command_with_json(func):
    """Add JSON option to a command function.

    Usage:
        @create_command_with_json
        def my_command(ctx: typer.Context, name: str, json_output: bool = False):
            use_json = should_use_json(ctx, json_output)
            # ... implementation

        # Then register normally:
        app.command("my-command")(my_command)
    """
    import functools

    @functools.wraps(func)
    def wrapper(ctx: typer.Context, *args, json_output: JsonOption = False, **kwargs):
        return func(ctx, *args, json_output=json_output, **kwargs)

    return wrapper
