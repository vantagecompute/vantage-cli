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
#!/usr/bin/env python3
"""Tests for simple_commands module."""

import inspect
from unittest.mock import Mock

import typer

from vantage_cli.simple_commands import (
    JsonOption,
    create_command_with_json,
    make_json_command,
    simple_command,
)


class TestJsonOption:
    """Test the JsonOption type annotation."""

    def test_json_option_is_annotated_bool(self):
        """Test that JsonOption is properly typed."""
        # Check that it contains typer.Option metadata
        assert hasattr(JsonOption, "__metadata__")
        metadata = getattr(JsonOption, "__metadata__")
        assert len(metadata) > 0
        assert isinstance(metadata[0], typer.models.OptionInfo)

        # Check the option configuration
        option_info = metadata[0]
        assert "-j" in option_info.param_decls
        assert option_info.help == "Output in JSON format"


class TestSimpleCommand:
    """Test the simple_command decorator."""

    def test_simple_command_registers_with_app(self):
        """Test that simple_command registers the command with the app."""
        app = typer.Typer()

        @simple_command(app, "test-cmd")
        def test_function(ctx: typer.Context):
            return "test result"

        # Check that the command was registered
        assert len(app.registered_commands) == 1
        command_info = app.registered_commands[0]
        assert command_info.name == "test-cmd"

    def test_simple_command_with_default_name(self):
        """Test simple_command when no name is provided."""
        app = typer.Typer()

        @simple_command(app)
        def test_function(ctx: typer.Context):
            return "test result"

        # Check that the command was registered with function name
        assert len(app.registered_commands) == 1
        command_info = app.registered_commands[0]
        assert command_info.name is None  # typer uses function name when None

    def test_simple_command_returns_original_function(self):
        """Test that simple_command returns the original function."""
        app = typer.Typer()

        def original_function(ctx: typer.Context):
            return "test result"

        decorated = simple_command(app, "test-cmd")(original_function)

        # The simple_command should return the original function
        # since it just calls app.command(name)(func)
        assert decorated is original_function

    def test_simple_command_preserves_function_signature(self):
        """Test that function signature is preserved."""
        app = typer.Typer()

        def test_function(ctx: typer.Context, name: str, json_output: bool = False):
            return f"Hello {name}"

        original_sig = inspect.signature(test_function)
        decorated = simple_command(app, "test-cmd")(test_function)
        new_sig = inspect.signature(decorated)

        assert str(original_sig) == str(new_sig)


class TestMakeJsonCommand:
    """Test the make_json_command function."""

    def test_make_json_command_registers_with_app(self):
        """Test that make_json_command registers the command."""
        app = typer.Typer()

        def impl_func(ctx: typer.Context, json_output: bool = False):
            return f"json: {json_output}"

        make_json_command(app, "test-cmd", impl_func)

        # Check that command was registered
        assert len(app.registered_commands) == 1
        command_info = app.registered_commands[0]
        assert command_info.name == "test-cmd"

    def test_make_json_command_with_help_text(self):
        """Test make_json_command with help text."""
        app = typer.Typer()

        def impl_func(ctx: typer.Context, json_output: bool = False):
            return f"json: {json_output}"

        make_json_command(app, "test-cmd", impl_func, "Test help text")

        # The wrapper should have the help text as docstring
        command_info = app.registered_commands[0]
        assert command_info.callback is not None
        assert command_info.callback.__doc__ == "Test help text"

    def test_make_json_command_wrapper_calls_impl(self):
        """Test that wrapper calls the implementation function."""
        app = typer.Typer()

        mock_impl = Mock(return_value="result")
        mock_impl.__name__ = "mock_impl"
        mock_impl.__doc__ = "Mock implementation"

        make_json_command(app, "test-cmd", mock_impl)

        # The wrapper should be registered as the callback
        command_info = app.registered_commands[0]
        assert command_info.callback is not None

        # Call the wrapper directly
        mock_ctx = Mock(spec=typer.Context)
        result = command_info.callback(mock_ctx, json_output=True, extra_kwarg="value")

        assert result == "result"
        mock_impl.assert_called_once_with(mock_ctx, json_output=True, extra_kwarg="value")

    def test_make_json_command_has_json_parameter(self):
        """Test that created command has json_output parameter."""
        app = typer.Typer()

        def impl_func(ctx: typer.Context, json_output: bool = False):
            return f"json: {json_output}"

        make_json_command(app, "test-cmd", impl_func)

        # Check the registered command callback signature
        command_info = app.registered_commands[0]
        assert command_info.callback is not None
        sig = inspect.signature(command_info.callback)
        assert "json_output" in sig.parameters
        assert sig.parameters["json_output"].default is False


class TestCreateCommandWithJson:
    """Test the create_command_with_json decorator."""

    def test_create_command_with_json_creates_wrapper(self):
        """Test that create_command_with_json creates a wrapper."""

        def sample_function(ctx: typer.Context, json_output: bool = False):
            return f"json: {json_output}"

        decorated = create_command_with_json(sample_function)

        # Check that it's a wrapper function
        assert decorated is not sample_function
        assert decorated.__name__ == sample_function.__name__
        assert decorated.__doc__ == sample_function.__doc__

    def test_create_command_with_json_works_functionally(self):
        """Test that wrapper works functionally with functions that accept json_output."""

        def sample_function(ctx: typer.Context, json_output: bool = False):
            return f"result, json: {json_output}"

        decorated = create_command_with_json(sample_function)

        # The wrapper should be callable and work correctly
        mock_ctx = Mock(spec=typer.Context)
        result = decorated(mock_ctx, json_output=True)
        assert result == "result, json: True"

        # Even though json_output doesn't appear in signature due to functools.wraps,
        # the wrapper internally handles the json_output parameter

    def test_create_command_with_json_calls_original(self):
        """Test that wrapper calls original function."""
        mock_func = Mock(return_value="result")
        mock_func.__name__ = "mock_func"
        mock_func.__doc__ = "Mock function"

        decorated = create_command_with_json(mock_func)

        mock_ctx = Mock(spec=typer.Context)
        result = decorated(mock_ctx, "arg1", "arg2", json_output=True, kwarg1="value")

        assert result == "result"
        mock_func.assert_called_once_with(
            mock_ctx, "arg1", "arg2", json_output=True, kwarg1="value"
        )

    def test_create_command_with_json_preserves_metadata(self):
        """Test that function metadata is preserved."""

        def sample_function(ctx: typer.Context):
            """Sample function docstring."""
            return "result"

        decorated = create_command_with_json(sample_function)

        assert decorated.__name__ == sample_function.__name__
        assert decorated.__doc__ == sample_function.__doc__

    def test_create_command_with_json_with_existing_json_param(self):
        """Test decorator with function that already has json_output."""

        def sample_function(ctx: typer.Context, name: str, json_output: bool = False):
            return f"Hello {name}, json: {json_output}"

        decorated = create_command_with_json(sample_function)

        # The wrapper should still work
        mock_ctx = Mock(spec=typer.Context)
        result = decorated(mock_ctx, "World", json_output=True)

        assert result == "Hello World, json: True"
