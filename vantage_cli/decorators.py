# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Vantage CLI command decorators - eliminates repetitive JSON option declarations."""

import functools

import typer
from typing_extensions import Annotated

# Standard JSON option - define once, use everywhere
JsonOption = Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")]


def vantage_command(app: typer.Typer, name: str | None = None, **command_kwargs):
    """Enhanced command decorator for Vantage CLI that automatically handles JSON option.

    This decorator wraps the standard typer.command decorator and automatically
    injects the --json option, so you don't need to include it in every function signature.

    Usage:
        @vantage_command(clouds_app, "list")
        def list_clouds(ctx: typer.Context, name: str, json_output: bool = False):
            use_json = should_use_json(ctx, json_output)
            # ... command logic

    Or use without specifying json_output in the signature:
        @vantage_command(clouds_app, "list")
        def list_clouds(ctx: typer.Context, name: str):
            use_json = should_use_json(ctx)  # Gets from global context
            # ... command logic
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(ctx: typer.Context, *args, json_output: JsonOption = False, **kwargs):
            # Call original function, passing json_output if it accepts it
            import inspect

            sig = inspect.signature(func)

            if "json_output" in sig.parameters:
                return func(ctx, *args, json_output=json_output, **kwargs)
            else:
                return func(ctx, *args, **kwargs)

        # Register the command with the app
        return app.command(name, **command_kwargs)(wrapper)

    return decorator


# Alternative simpler approach - use a consistent pattern
def json_enabled_command(func):
    """Ensure a command function handles JSON consistently.

    Usage:
        @app.command("list")
        @json_enabled_command
        def list_items(ctx: typer.Context, name: str, json_output: bool = False):
            use_json = should_use_json(ctx, json_output)
            # ... command logic
    """

    @functools.wraps(func)
    def wrapper(ctx: typer.Context, *args, json_output: JsonOption = False, **kwargs):
        return func(ctx, *args, json_output=json_output, **kwargs)

    return wrapper


# Most practical: Just create template functions
def create_cloud_command(app, name, func, help_text=None):
    """Register cloud commands with standard JSON handling.

    Usage:
        def list_impl(ctx, json_output=False):
            use_json = should_use_json(ctx, json_output)
            # ... implementation

        create_cloud_command(clouds_app, "list", list_impl, "List all clouds")
    """

    @functools.wraps(func)
    def wrapper(ctx: typer.Context, json_output: JsonOption = False, **kwargs):
        return func(ctx, json_output=json_output, **kwargs)

    if help_text:
        wrapper.__doc__ = help_text

    return app.command(name)(wrapper)
