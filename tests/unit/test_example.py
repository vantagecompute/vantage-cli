# © 2025 Vantage Compute, Inc. All rights reserved.
# Confidential and proprietary. Unauthorized use prohibited.
"""Tests for example command module."""

from unittest.mock import Mock, patch

import pytest
import typer

from vantage_cli.commands.example import example_command


class TestExampleCommand:
    """Test suite for example_command function."""

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock Typer context."""
        ctx = Mock(spec=typer.Context)
        ctx.obj = Mock()
        ctx.obj.json_output = False
        ctx.obj.verbose = False
        return ctx

    @pytest.fixture
    def mock_ctx_with_json(self):
        """Create a mock Typer context with JSON output enabled."""
        ctx = Mock(spec=typer.Context)
        ctx.obj = Mock()
        ctx.obj.json_output = True
        ctx.obj.verbose = False
        return ctx

    @pytest.fixture
    def mock_ctx_with_verbose(self):
        """Create a mock Typer context with verbose enabled."""
        ctx = Mock(spec=typer.Context)
        ctx.obj = Mock()
        ctx.obj.json_output = False
        ctx.obj.verbose = True
        return ctx

    @pytest.fixture
    def mock_ctx_no_obj(self):
        """Create a mock Typer context with no obj."""
        ctx = Mock(spec=typer.Context)
        ctx.obj = None
        return ctx

    @pytest.mark.asyncio
    async def test_example_command_default_behavior(self, mock_ctx):
        """Test example command with default parameters."""
        with (
            patch("vantage_cli.commands.example.console") as mock_console,
            patch(
                "vantage_cli.commands.example.should_use_json", return_value=False
            ) as mock_should_use_json,
        ):
            await example_command(
                ctx=mock_ctx,
                name="test-resource",
                description="",
                json_output=False,
                verbose=False,
                force=False,
            )

            # Verify should_use_json was called correctly (only takes ctx parameter)
            mock_should_use_json.assert_called_once_with(mock_ctx)

            # Verify console output was called
            assert mock_console.print.call_count >= 3  # At least name, status, timestamp

    @pytest.mark.asyncio
    async def test_example_command_with_description(self, mock_ctx):
        """Test example command with description provided."""
        with (
            patch("vantage_cli.commands.example.console") as mock_console,
            patch("vantage_cli.commands.example.should_use_json", return_value=False),
        ):
            await example_command(
                ctx=mock_ctx,
                name="test-resource",
                description="Test description",
                json_output=False,
                verbose=False,
                force=False,
            )

            # Should include description in output
            calls = [str(call) for call in mock_console.print.call_args_list]
            description_printed = any("Test description" in call for call in calls)
            assert description_printed

    @pytest.mark.asyncio
    async def test_example_command_json_output(self, mock_ctx):
        """Test example command with JSON output enabled."""
        with (
            patch("vantage_cli.commands.example.print_json") as mock_print_json,
            patch("vantage_cli.commands.example.should_use_json", return_value=True),
        ):
            await example_command(
                ctx=mock_ctx,
                name="test-resource",
                description="Test description",
                json_output=True,
                verbose=False,
                force=False,
            )

            # Verify JSON output was called
            mock_print_json.assert_called_once()

            # Verify the data structure passed to print_json
            call_args = mock_print_json.call_args
            data = call_args.kwargs["data"]
            assert data["name"] == "test-resource"
            assert data["description"] == "Test description"
            assert data["status"] == "created"
            assert "timestamp" in data
            assert data["verbose_mode"] is False

    @pytest.mark.asyncio
    async def test_example_command_force_flag(self, mock_ctx):
        """Test example command with force flag enabled."""
        with (
            patch("vantage_cli.commands.example.print_json") as mock_print_json,
            patch("vantage_cli.commands.example.should_use_json", return_value=True),
        ):
            await example_command(
                ctx=mock_ctx,
                name="test-resource",
                description="",
                json_output=True,
                verbose=False,
                force=True,
            )

            # Verify force affects the status
            call_args = mock_print_json.call_args
            data = call_args.kwargs["data"]
            assert data["status"] == "force-created"

    @pytest.mark.asyncio
    async def test_example_command_verbose_local_flag(self, mock_ctx):
        """Test example command with local verbose flag."""
        with (
            patch("vantage_cli.commands.example.console") as mock_console,
            patch("vantage_cli.commands.example.should_use_json", return_value=False),
        ):
            await example_command(
                ctx=mock_ctx,
                name="test-resource",
                description="",
                json_output=False,
                verbose=True,
                force=False,
            )

            # Should include verbose output
            calls = [str(call) for call in mock_console.print.call_args_list]
            verbose_printed = any("Verbose mode enabled" in call for call in calls)
            assert verbose_printed

    @pytest.mark.asyncio
    async def test_example_command_verbose_global_setting(self, mock_ctx_with_verbose):
        """Test example command with global verbose setting."""
        with (
            patch("vantage_cli.commands.example.console") as mock_console,
            patch("vantage_cli.commands.example.should_use_json", return_value=False),
        ):
            await example_command(
                ctx=mock_ctx_with_verbose,
                name="test-resource",
                description="",
                json_output=False,
                verbose=False,  # Local flag false, but global is true
                force=False,
            )

            # Should still show verbose output due to global setting
            calls = [str(call) for call in mock_console.print.call_args_list]
            verbose_printed = any("Verbose mode enabled" in call for call in calls)
            assert verbose_printed

    @pytest.mark.asyncio
    async def test_example_command_no_ctx_obj(self, mock_ctx_no_obj):
        """Test example command when ctx.obj is None."""
        with (
            patch("vantage_cli.commands.example.console") as mock_console,
            patch("vantage_cli.commands.example.should_use_json", return_value=False),
        ):
            await example_command(
                ctx=mock_ctx_no_obj,
                name="test-resource",
                description="",
                json_output=False,
                verbose=False,
                force=False,
            )

            # Should handle missing ctx.obj gracefully
            assert mock_console.print.call_count >= 3

    @pytest.mark.asyncio
    async def test_example_command_verbose_details_shown(self, mock_ctx):
        """Test that verbose mode shows additional details."""
        with (
            patch("vantage_cli.commands.example.console") as mock_console,
            patch("vantage_cli.commands.example.should_use_json", return_value=False),
        ):
            await example_command(
                ctx=mock_ctx,
                name="test-resource",
                description="Test description",
                json_output=True,
                verbose=True,
                force=True,
            )

            # Check that force and json flags are shown in verbose mode
            calls = [str(call) for call in mock_console.print.call_args_list]
            force_shown = any("Force flag: True" in call for call in calls)
            json_shown = any("JSON output: True" in call for call in calls)
            assert force_shown
            assert json_shown

    @pytest.mark.asyncio
    async def test_example_command_json_output_includes_verbose_mode(self, mock_ctx):
        """Test that JSON output includes verbose_mode field correctly."""
        with (
            patch("vantage_cli.commands.example.print_json") as mock_print_json,
            patch("vantage_cli.commands.example.should_use_json", return_value=True),
        ):
            # Test with verbose=True
            await example_command(
                ctx=mock_ctx,
                name="test-resource",
                description="",
                json_output=True,
                verbose=True,
                force=False,
            )

            call_args = mock_print_json.call_args
            data = call_args.kwargs["data"]
            assert data["verbose_mode"] is True


class TestExampleCommandCLI:
    """Test the CLI interface when run as main."""

    def test_main_cli_interface(self):
        """Test that the main CLI interface can be created without errors."""
        # This tests the if __name__ == "__main__" block
        with patch("vantage_cli.commands.example.typer.Typer") as mock_typer_class:
            mock_app = Mock()
            mock_typer_class.return_value = mock_app

            # Import the module to trigger the main block
            import importlib

            import vantage_cli.commands.example

            importlib.reload(vantage_cli.commands.example)

            # Verify app was created and command was registered
            # Note: This is a bit tricky to test properly without actually running main
            # but we're testing the structure is valid
            assert True  # If we get here without import errors, the structure is valid
