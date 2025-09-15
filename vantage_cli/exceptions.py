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
"""Exception handling and error management for the Vantage CLI."""

import inspect
from functools import wraps
from sys import exc_info

import buzz
import snick
import typer
from loguru import logger
from rich.console import Console
from rich.panel import Panel

# Enables prettified traceback printing via rich - we'll install this conditionally
# traceback.install()  # Commented out to avoid showing tracebacks in normal mode


class VantageCliError(buzz.Buzz):
    """Base exception class for Vantage CLI errors."""

    pass


class DeploymentError(VantageCliError):
    """Exception for deployment-related failures."""

    pass


class ValidationError(VantageCliError):
    """Exception for data validation failures."""

    pass


class ConfigurationError(VantageCliError):
    """Exception for configuration-related issues."""

    pass


class AuthenticationError(VantageCliError):
    """Exception for authentication and authorization failures."""

    pass


class ApiError(VantageCliError):
    """Exception for API communication failures."""

    pass


class Abort(buzz.Buzz):
    """Exception class for aborting operations with user-friendly messages."""

    def __init__(
        self,
        message,
        *args,
        subject=None,
        log_message=None,
        warn_only=False,
        **kwargs,
    ):
        self.subject = subject
        self.log_message = log_message
        self.warn_only = warn_only
        (_, self.original_error, __) = exc_info()
        super().__init__(message, *args, **kwargs)


def _handle_authentication_error(auth_err: AuthenticationError) -> None:
    """Handle authentication errors with consistent messaging."""
    message = (
        "Authentication failed. Your token may be expired or invalid.\n\n"
        "Please run 'vantage login' to authenticate again."
    )
    console = Console()
    console.print()
    console.print(Panel(message, title="[red]Authentication Required"))
    console.print()
    logger.error(f"Authentication error: {auth_err}")
    raise typer.Exit(code=1)


def _handle_abort_error(err: Abort) -> None:
    """Handle abort errors with consistent messaging."""
    if not err.warn_only:
        if err.log_message is not None:
            logger.error(err.log_message)

        if err.original_error is not None:
            logger.error(f"Original exception: {err.original_error}")

    panel_kwargs = {}
    if err.subject is not None:
        panel_kwargs["title"] = f"[red]{err.subject}"
    message = snick.dedent(err.message)

    console = Console()
    console.print()
    console.print(Panel(message, **panel_kwargs))
    console.print()
    raise typer.Exit(code=1)


def handle_abort(func):
    """Handle abort exceptions in decorated functions."""
    if inspect.iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except AuthenticationError as auth_err:
                _handle_authentication_error(auth_err)
            except Abort as err:
                _handle_abort_error(err)

        return async_wrapper
    else:

        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except AuthenticationError as auth_err:
                _handle_authentication_error(auth_err)
            except Abort as err:
                _handle_abort_error(err)

        return wrapper
