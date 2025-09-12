"""Vantage CLI package for managing cloud computing resources."""

import asyncio
import importlib.metadata
import inspect
from typing import Any, Callable, Optional

import typer
from pydantic import BaseModel, ConfigDict
from typing_extensions import Annotated

__version__ = importlib.metadata.version("vantage-cli")


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
                # Extract and store injected parameters in context
                if hasattr(ctx, "obj") and ctx.obj is not None:
                    # Handle json parameter
                    json_flag = kwargs.pop("json", False)
                    ctx.obj.json_output = json_flag or getattr(ctx.obj, "json_output", False)

                    # Handle verbose parameter
                    verbose_flag = kwargs.pop("verbose", False)
                    ctx.obj.verbose = verbose_flag or getattr(ctx.obj, "verbose", False)

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
                use_json = should_use_json(ctx, json_output)
                # ... command logic
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
