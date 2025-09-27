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
"""Vantage CLI package for managing cloud computing resources."""

import asyncio
import importlib.metadata
import inspect
import logging
import sys
import time
from functools import wraps
from typing import Any, Callable, List, Optional  # noqa: F401

import typer
from pydantic import BaseModel, ConfigDict
from typing_extensions import Annotated

from vantage_cli.constants import VANTAGE_CLI_DEBUG_LOG_PATH

__version__ = importlib.metadata.version("vantage-cli")

# Global variable to track the file logging handler
_file_handler: Optional[logging.Handler] = None
_logging_initialized: bool = False

# Add a null handler at import time to prevent logs from being lost
# This handler will be replaced by setup_logging()
logging.getLogger().addHandler(logging.NullHandler())


def setup_logging(verbose: bool = False) -> None:
    """Configure logging based on verbosity flag.

    File logging to ~/.vantage-cli/debug.log is always enabled.

    Args:
        verbose: If True, enable DEBUG level logging to console
    """
    global _file_handler, _logging_initialized

    # Get the root logger
    root_logger = logging.getLogger()

    # Only remove handlers if we've already configured logging before
    # On first call, there shouldn't be any handlers
    if _logging_initialized:
        # Remove existing handlers except file handler
        handlers_to_remove = [h for h in root_logger.handlers if h != _file_handler]
        for handler in handlers_to_remove:
            root_logger.removeHandler(handler)

    if verbose:
        console_level = logging.DEBUG
        # Enable rich tracebacks only in verbose mode
        from rich import traceback

        traceback.install()
        logging.getLogger("httpx").disabled = False
        logging.getLogger("httpcore").disabled = False
    else:
        console_level = logging.ERROR
        # Disable rich tracebacks in normal mode
        sys.excepthook = sys.__excepthook__

    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # Set root logger level to DEBUG to capture all logs for file handler
    # Console handler will filter based on its own level
    root_logger.setLevel(logging.DEBUG)

    # IMPORTANT: Reset all existing loggers to ensure they pick up the new level
    # This is necessary because loggers created before setup_logging() may have
    # cached their effective level
    for logger_name in list(logging.Logger.manager.loggerDict.keys()):
        logger_instance = logging.getLogger(logger_name)
        # Only reset level for loggers in our namespace
        if logger_name.startswith("vantage_cli"):
            logger_instance.setLevel(logging.NOTSET)  # Inherit from root

    _logging_initialized = True

    if _file_handler is None:
        from logging.handlers import RotatingFileHandler

        VANTAGE_CLI_DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

        _file_handler = RotatingFileHandler(
            VANTAGE_CLI_DEBUG_LOG_PATH,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=7,
        )
        _file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        _file_handler.setFormatter(file_formatter)
        root_logger.addHandler(_file_handler)

    logger = logging.getLogger(__name__)
    logger.debug(
        "Logging configured (verbose=%s, file_logging=always_enabled)",
        verbose,
    )


def maybe_run_async(func: Callable) -> Callable:
    """Wrap async functions for use in Typer commands.

    This wraps an async function so it can be used as a Typer command.
    When the command is invoked, it will run the async function in an event loop.

    Args:
        func: The async function to wrap

    Returns:
        A wrapper function that runs the async function in an event loop
    """
    if not inspect.iscoroutinefunction(func):
        # Function is not async, return as-is
        return func

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        """Run the async function in an event loop."""
        try:
            # Check if we're already in an event loop
            asyncio.get_running_loop()
            # We're in an event loop, cannot use asyncio.run()
            # Return the coroutine directly (for tests)
            return func(*args, **kwargs)
        except RuntimeError:
            # No event loop running, safe to use asyncio.run()
            return asyncio.run(func(*args, **kwargs))

    return wrapper


class TyperCommandParameter(BaseModel):
    """Represents a command parameter that can be automatically injected."""

    name: str
    type: Any  # Will hold inspect.Parameter.KEYWORD_ONLY
    default: Any
    annotation: Any

    model_config = ConfigDict(arbitrary_types_allowed=True)


# Define common parameters that will be injected into all commands
inherited_command_parameters = [
    TyperCommandParameter(
        name="json",
        type=inspect.Parameter.KEYWORD_ONLY,
        default=False,
        annotation=Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")],
    ),
    TyperCommandParameter(
        name="verbose",
        type=inspect.Parameter.KEYWORD_ONLY,
        default=False,
        annotation=Annotated[
            bool, typer.Option("--verbose", "-v", help="Enable verbose terminal output")
        ],
    ),
    TyperCommandParameter(
        name="profile",
        type=inspect.Parameter.KEYWORD_ONLY,
        default="default",
        annotation=Annotated[str, typer.Option("--profile", "-p", help="Profile name to use")],
    ),
]


class AsyncTyper(typer.Typer):
    """A Typer subclass that automatically wraps async functions with asyncio.run()."""

    @staticmethod
    def format_elapsed_time(start_time: float) -> str:
        """Format elapsed time from start_time to current time with high granularity.

        Args:
            start_time: Start time from time.time()

        Returns:
            Formatted time string like "0:05.123", "1:23:45.678", or "0.123s"
        """
        elapsed = time.time() - start_time

        # For very short times (< 1 second), show milliseconds only
        if elapsed < 1.0:
            return f"{elapsed:.3f}s"

        # For times >= 1 second, show with millisecond precision
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = elapsed % 60  # Keep as float for milliseconds

        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:06.3f}"
        else:
            return f"{minutes}:{seconds:06.3f}"

    @staticmethod
    def get_elapsed_time(ctx: typer.Context) -> str:
        """Get formatted elapsed time from context.

        Args:
            ctx: Typer context with command_start_time attribute

        Returns:
            Formatted elapsed time or "0.000s" if no timing available
        """
        if hasattr(ctx, "obj") and ctx.obj and hasattr(ctx.obj, "command_start_time"):
            return AsyncTyper.format_elapsed_time(ctx.obj.command_start_time)
        return "0.000s"

    @staticmethod
    def get_command_start_time(ctx: typer.Context) -> Optional[float]:
        """Get command start time from context.

        Args:
            ctx: Typer context with command_start_time attribute

        Returns:
            Command start time or None if not available
        """
        if hasattr(ctx, "obj") and ctx.obj and hasattr(ctx.obj, "command_start_time"):
            return ctx.obj.command_start_time
        return None

    @staticmethod
    def maybe_run_async(func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Run function asynchronously if it's a coroutine, otherwise run normally."""
        if inspect.iscoroutinefunction(func):
            # Check if we're already in an event loop
            try:
                asyncio.get_running_loop()
                # We're in an event loop, cannot use asyncio.run()
                # This typically happens in tests, return the coroutine
                return func(*args, **kwargs)
            except RuntimeError:
                # No event loop running, safe to use asyncio.run()
                return asyncio.run(func(*args, **kwargs))
        else:
            # Check if the function call returns a coroutine
            result = func(*args, **kwargs)
            if inspect.iscoroutine(result):
                # Function returned a coroutine, need to run it
                try:
                    asyncio.get_running_loop()
                    # We're in an event loop, return the coroutine
                    return result
                except RuntimeError:
                    # No event loop running, safe to use asyncio.run()
                    return asyncio.run(result)
            return result

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
        """Override command decorator to handle async functions and auto-inject common options."""

        def decorator(func: Callable) -> Callable:
            import functools

            # Get the original function's signature
            original_sig = inspect.signature(func)
            new_params = list(original_sig.parameters.values())

            # Inject inherited command parameters if they don't already exist
            for cmd_param in inherited_command_parameters:
                if cmd_param.name not in original_sig.parameters:
                    # Create the parameter with the correct attributes
                    param = inspect.Parameter(
                        name=cmd_param.name,
                        kind=inspect.Parameter.KEYWORD_ONLY,
                        default=cmd_param.default,
                        annotation=cmd_param.annotation,
                    )
                    new_params.append(param)

            # Create new signature with all injected parameters
            new_sig = original_sig.replace(parameters=new_params)

            # Create a wrapper that handles the injected parameters
            def command_wrapper(ctx: typer.Context, *args: Any, **kwargs: Any) -> Any:
                # Start timing the command execution
                command_start_time = time.time()

                # Extract and store injected parameters in context
                if hasattr(ctx, "obj") and ctx.obj is not None:
                    # Store the start time in the context for later use
                    ctx.obj.command_start_time = command_start_time

                    # Handle json parameter
                    json_flag = kwargs.pop("json", False)
                    ctx.obj.json_output = json_flag or getattr(ctx.obj, "json_output", False)

                    # Update the formatter's json_output flag if formatter exists
                    if hasattr(ctx.obj, "formatter") and ctx.obj.formatter is not None:
                        ctx.obj.formatter.json_output = ctx.obj.json_output

                    # Handle verbose parameter
                    verbose_flag = kwargs.pop("verbose", False)
                    ctx.obj.verbose = verbose_flag or getattr(ctx.obj, "verbose", False)

                    setup_logging(verbose=ctx.obj.verbose)

                    # Handle profile parameter
                    profile_value = kwargs.pop("profile", "default")
                    if not hasattr(ctx.obj, "profile") or ctx.obj.profile == "default":
                        ctx.obj.profile = profile_value

                # Call the original function without the injected parameters
                return func(ctx, *args, **kwargs)

            # Set the new signature on the wrapper
            command_wrapper.__signature__ = new_sig  # type: ignore[misc]
            command_wrapper.__name__ = func.__name__
            command_wrapper.__doc__ = func.__doc__
            command_wrapper.__module__ = func.__module__
            command_wrapper.__qualname__ = func.__qualname__
            command_wrapper.__annotations__ = func.__annotations__.copy()

            # Handle async functions
            if inspect.iscoroutinefunction(func):

                @functools.wraps(command_wrapper)
                def sync_wrapper(*args, **kwargs):
                    return self.maybe_run_async(command_wrapper, *args, **kwargs)

                wrapped_func = sync_wrapper
                # Copy signature to sync wrapper too
                wrapped_func.__signature__ = new_sig  # type: ignore[misc]
            else:
                wrapped_func = command_wrapper

            # Build kwargs for parent method, filtering out None values
            command_kwargs = {
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
                command_kwargs["options_metavar"] = options_metavar

            return super(AsyncTyper, self).command(**command_kwargs)(wrapped_func)

        return decorator

    def app_command(
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
        """Command decorator that automatically handles async functions and provides a consistent pattern.

        This decorator can be extended to automatically inject common options in the future.
        For now, it provides the same functionality as the standard command decorator.

        Usage:
            @app.app_command()
            def my_command(ctx: typer.Context, name: str, json_output: JsonOption = False):
                if should_use_json(ctx):
                    # JSON output logic
                else:
                    # Rich/interactive output logic
        """
        return self.command(
            name=name,
            cls=cls,
            context_settings=context_settings,
            help=help,
            epilog=epilog,
            short_help=short_help,
            options_metavar=options_metavar,
            add_help_option=add_help_option,
            no_args_is_help=no_args_is_help,
            hidden=hidden,
            deprecated=deprecated,
            rich_help_panel=rich_help_panel,
        )

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
