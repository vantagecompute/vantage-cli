"""Vantage CLI package for managing cloud computing resources."""

import asyncio
import importlib.metadata
import inspect
from typing import Any, Callable, Optional

import typer

__version__ = importlib.metadata.version("vantage-cli")


class AsyncTyper(typer.Typer):
    """A Typer subclass that automatically wraps async functions with asyncio.run()."""

    @staticmethod
    def maybe_run_async(func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Run function asynchronously if it's a coroutine, otherwise run normally."""
        if inspect.iscoroutinefunction(func):
            return asyncio.run(func(*args, **kwargs))
        return func(*args, **kwargs)

    def command(
        self,
        name: Optional[str] = None,
        *,
        cls: Optional[type] = None,
        context_settings: Optional[dict] = None,
        help: Optional[str] = None,
        epilog: Optional[str] = None,
        short_help: Optional[str] = None,
        options_metavar: Optional[str] = None,
        add_help_option: bool = True,
        no_args_is_help: bool = False,
        hidden: bool = False,
        deprecated: bool = False,
        rich_help_panel: Optional[str] = None,
    ):
        """Override command decorator to handle async functions."""

        def decorator(func: Callable) -> Callable:
            if inspect.iscoroutinefunction(func):
                # Create a sync wrapper that preserves the original function signature
                import functools

                @functools.wraps(func)
                def sync_wrapper(*args, **kwargs):
                    return self.maybe_run_async(func, *args, **kwargs)

                wrapped_func = sync_wrapper
            else:
                wrapped_func = func

            # Build kwargs for parent method, filtering out None values
            kwargs = {
                "name": name,
                "cls": cls,
                "context_settings": context_settings,
                "help": help,
                "epilog": epilog,
                "short_help": short_help,
                "add_help_option": add_help_option,
                "no_args_is_help": no_args_is_help,
                "hidden": hidden,
                "deprecated": deprecated,
                "rich_help_panel": rich_help_panel,
            }
            if options_metavar is not None:
                kwargs["options_metavar"] = options_metavar

            return super(AsyncTyper, self).command(**kwargs)(wrapped_func)

        return decorator

    def callback(
        self,
        *,
        cls: Optional[type] = None,
        invoke_without_command: bool = False,
        no_args_is_help: bool = False,
        subcommand_metavar: Optional[str] = None,
        chain: bool = False,
        result_callback: Optional[Callable] = None,
        context_settings: Optional[dict] = None,
        help: Optional[str] = None,
        epilog: Optional[str] = None,
        short_help: Optional[str] = None,
        options_metavar: Optional[str] = None,
        add_help_option: bool = True,
        hidden: bool = False,
        deprecated: bool = False,
        rich_help_panel: Optional[str] = None,
    ):
        """Override callback decorator to handle async functions."""

        def decorator(func: Callable) -> Callable:
            if inspect.iscoroutinefunction(func):
                # Create a sync wrapper that preserves the original function signature
                import functools

                @functools.wraps(func)
                def sync_wrapper(*args, **kwargs):
                    return self.maybe_run_async(func, *args, **kwargs)

                wrapped_func = sync_wrapper
            else:
                wrapped_func = func

            # Build kwargs for parent method, filtering out None values
            kwargs = {
                "cls": cls,
                "invoke_without_command": invoke_without_command,
                "no_args_is_help": no_args_is_help,
                "subcommand_metavar": subcommand_metavar,
                "chain": chain,
                "result_callback": result_callback,
                "context_settings": context_settings,
                "help": help,
                "epilog": epilog,
                "short_help": short_help,
                "add_help_option": add_help_option,
                "hidden": hidden,
                "deprecated": deprecated,
                "rich_help_panel": rich_help_panel,
            }
            if options_metavar is not None:
                kwargs["options_metavar"] = options_metavar

            return super(AsyncTyper, self).callback(**kwargs)(wrapped_func)

        return decorator
