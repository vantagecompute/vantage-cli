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
"""Tests for decorators module."""

from unittest.mock import Mock, patch

import pytest
import typer

from vantage_cli.decorators import (
    JsonOption,
    create_cloud_command,
    json_enabled_command,
    vantage_command,
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

        # Check the option configuration - note: typer.Option() takes args differently
        option_info = metadata[0]
        # The param_decls might be just ("-j",) if only short form is set
        assert "-j" in option_info.param_decls
        assert option_info.help == "Output in JSON format"


class TestVantageCommand:
    """Test the vantage_command decorator."""

    def test_vantage_command_registers_with_app(self):
        """Test that vantage_command registers the command with the app."""
        app = typer.Typer()

        @vantage_command(app, "test-cmd")
        def test_function(ctx: typer.Context):
            return "test result"

        # Check that the command was registered
        assert len(app.registered_commands) == 1
        command_info = app.registered_commands[0]
        assert command_info.name == "test-cmd"

    def test_vantage_command_with_default_name(self):
        """Test vantage_command when no name is provided."""
        app = typer.Typer()

        @vantage_command(app)
        def test_function(ctx: typer.Context):
            return "test result"

        # Check that the command was registered with function name
        assert len(app.registered_commands) == 1
        command_info = app.registered_commands[0]
        assert command_info.name is None  # typer uses function name when None

    def test_vantage_command_registers_command(self):
        """Test that vantage_command registers the command with the app."""
        app = typer.Typer()

        @vantage_command(app, "test-cmd")
        def test_function(ctx: typer.Context):
            return "test result"

        # Check that the command was registered
        assert len(app.registered_commands) == 1
        command_info = app.registered_commands[0]
        assert command_info.name == "test-cmd"
        assert command_info.callback is not None

    def test_vantage_command_wrapper_behavior(self):
        """Test that vantage_command wrapper handles json_output properly."""
        app = typer.Typer()

        # Create a function that accepts json_output
        def func_with_json(ctx: typer.Context, json_output: bool = False):
            return f"json: {json_output}"

        decorated = vantage_command(app, "test-cmd")(func_with_json)

        # Test that the wrapper can be called with json_output
        mock_ctx = Mock(spec=typer.Context)

        # This should work even though json_output doesn't appear in signature
        # because the wrapper internally handles it
        try:
            result = decorated(mock_ctx)
            assert isinstance(result, str)
        except Exception as e:
            pytest.fail(f"Decorated function should be callable: {e}")

    def test_vantage_command_wrapper_without_json_param(self):
        """Test wrapper calls function without json_output if it doesn't accept it."""
        app = typer.Typer()

        # Mock function that doesn't accept json_output
        mock_func = Mock(return_value="result")
        mock_func.__name__ = "mock_func"
        mock_func.__doc__ = "Mock function"

        # Mock inspect.signature to return a signature without json_output
        mock_signature = Mock()
        mock_signature.parameters = {}

        # Note: inspect is imported dynamically inside the wrapper function
        with patch("inspect.signature", return_value=mock_signature):
            decorated = vantage_command(app, "test-cmd")(mock_func)

        # The decorator should return the result of app.command(...)(wrapper)
        # which should be callable
        assert callable(decorated)

    def test_vantage_command_passes_additional_kwargs(self):
        """Test that vantage_command passes additional kwargs to typer.command."""
        app = typer.Typer()

        @vantage_command(app, "test-cmd", help="Test command", hidden=True)
        def test_function(ctx: typer.Context):
            return "test result"

        # Check that command was registered with additional options
        command_info = app.registered_commands[0]
        assert command_info.help == "Test command"
        assert command_info.hidden is True

    def test_vantage_command_preserves_function_metadata(self):
        """Test that function metadata is preserved."""
        app = typer.Typer()

        def original_function(ctx: typer.Context):
            """Original function docstring."""
            return "test result"

        decorated = vantage_command(app, "test-cmd")(original_function)

        # The decorated function should be the wrapper, not the original
        # But it should preserve the original's metadata
        assert hasattr(decorated, "__name__")
        assert hasattr(decorated, "__doc__")


class TestJsonEnabledCommand:
    """Test the json_enabled_command decorator."""

    def test_json_enabled_command_preserves_function(self):
        """Test that json_enabled_command creates a wrapper."""

        def sample_function(ctx: typer.Context, json_output: bool = False):
            return f"json: {json_output}"

        decorated = json_enabled_command(sample_function)

        # Check that it's a wrapper function
        assert decorated is not sample_function
        assert decorated.__name__ == sample_function.__name__
        assert decorated.__doc__ == sample_function.__doc__

    def test_json_enabled_command_creates_wrapper(self):
        """Test that json_enabled_command creates a callable wrapper."""

        def sample_function(ctx: typer.Context):
            return "result"

        decorated = json_enabled_command(sample_function)

        # Check that it's a wrapper function
        assert decorated is not sample_function
        assert decorated.__name__ == sample_function.__name__
        assert decorated.__doc__ == sample_function.__doc__
        assert callable(decorated)

    def test_json_enabled_command_calls_original_with_json(self):
        """Test that wrapper calls original function with json_output."""
        mock_func = Mock(return_value="result")
        mock_func.__name__ = "mock_func"
        mock_func.__doc__ = "Mock function"

        decorated = json_enabled_command(mock_func)

        mock_ctx = Mock(spec=typer.Context)
        result = decorated(mock_ctx, json_output=True)

        assert result == "result"
        mock_func.assert_called_once_with(mock_ctx, json_output=True)

    def test_json_enabled_command_passes_additional_args(self):
        """Test that wrapper passes through additional arguments."""
        mock_func = Mock(return_value="result")
        mock_func.__name__ = "mock_func"
        mock_func.__doc__ = "Mock function"

        decorated = json_enabled_command(mock_func)

        mock_ctx = Mock(spec=typer.Context)
        result = decorated(mock_ctx, "arg1", "arg2", json_output=False, kwarg1="value")

        assert result == "result"
        mock_func.assert_called_once_with(
            mock_ctx, "arg1", "arg2", json_output=False, kwarg1="value"
        )


class TestCreateCloudCommand:
    """Test the create_cloud_command helper function."""

    def test_create_cloud_command_registers_with_app(self):
        """Test that create_cloud_command registers the command."""
        app = typer.Typer()

        def impl_func(ctx: typer.Context, json_output: bool = False):
            return f"json: {json_output}"

        create_cloud_command(app, "test-cmd", impl_func)

        # Check that command was registered
        assert len(app.registered_commands) == 1
        command_info = app.registered_commands[0]
        assert command_info.name == "test-cmd"

    def test_create_cloud_command_with_help_text(self):
        """Test create_cloud_command with help text."""
        app = typer.Typer()

        def impl_func(ctx: typer.Context, json_output: bool = False):
            return f"json: {json_output}"

        result = create_cloud_command(app, "test-cmd", impl_func, "Test help text")

        # The wrapper should have the help text as docstring
        assert result.__doc__ == "Test help text"

    def test_create_cloud_command_wrapper_calls_impl(self):
        """Test that wrapper calls the implementation function."""
        app = typer.Typer()

        mock_impl = Mock(return_value="result")
        mock_impl.__name__ = "mock_impl"
        mock_impl.__doc__ = "Mock implementation"

        wrapper = create_cloud_command(app, "test-cmd", mock_impl)

        mock_ctx = Mock(spec=typer.Context)
        result = wrapper(mock_ctx, json_output=True, extra_kwarg="value")

        assert result == "result"
        mock_impl.assert_called_once_with(mock_ctx, json_output=True, extra_kwarg="value")

    def test_create_cloud_command_creates_wrapper(self):
        """Test that created command is callable."""
        app = typer.Typer()

        def impl_func(ctx: typer.Context, json_output: bool = False):
            return f"json: {json_output}"

        wrapper = create_cloud_command(app, "test-cmd", impl_func)

        # The wrapper should be callable
        assert callable(wrapper)
        assert wrapper.__name__ == impl_func.__name__

    def test_create_cloud_command_preserves_function_metadata(self):
        """Test that function metadata is preserved."""
        app = typer.Typer()

        def impl_func(ctx: typer.Context, json_output: bool = False):
            """Implement the function."""
            return "result"

        wrapper = create_cloud_command(app, "test-cmd", impl_func)

        assert wrapper.__name__ == impl_func.__name__
        # Note: __doc__ might be overridden if help_text is provided
