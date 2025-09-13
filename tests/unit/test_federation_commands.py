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
"""Comprehensive tests for federation commands."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
import typer

# Import the functions we want to test
try:
    from vantage_cli.commands.cluster.federation.create import create_federation
    from vantage_cli.commands.cluster.federation.delete import delete_federation
    from vantage_cli.commands.cluster.federation.get import get_federation
    from vantage_cli.commands.cluster.federation.list import list_federations
    from vantage_cli.commands.cluster.federation.update import update_federation
except ImportError:
    # Handle import errors during testing
    pytest.skip("Federation module not available", allow_module_level=True)


class TestFederationList:
    """Test federation list functionality."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock typer context."""
        ctx = Mock(spec=typer.Context)
        ctx.params = {"json_output": False}
        ctx.obj = SimpleNamespace(profile="default", verbose=False, json_output=False)
        return ctx

    @patch("vantage_cli.commands.cluster.federation.list.get_effective_json_output")
    @patch("vantage_cli.commands.cluster.federation.list.print_json")
    def test_list_federations_json_output(
        self, mock_print_json, mock_get_json_output, mock_context
    ):
        """Test list federations with JSON output."""
        mock_get_json_output.return_value = True
        mock_context.obj.json_output = True
        # Run the command
        import asyncio

        asyncio.run(list_federations(mock_context))

        # Verify JSON output was called with stub data
        mock_print_json.assert_called_once()
        call_args = mock_print_json.call_args[1]
        assert "data" in call_args
        assert "federations" in call_args["data"]
        assert "total" in call_args["data"]
        assert call_args["data"]["total"] == 0
        assert call_args["data"]["message"] == "Federation list command not yet implemented"

    @patch("vantage_cli.commands.cluster.federation.list.get_effective_json_output")
    @patch("vantage_cli.commands.cluster.federation.list.Console")
    def test_list_federations_console_output(
        self, mock_console_class, mock_get_json_output, mock_context
    ):
        """Test list federations with console output."""
        mock_get_json_output.return_value = False
        mock_console = Mock()
        mock_console_class.return_value = mock_console
        mock_context.obj.json_output = False
        # Run the command
        import asyncio

        asyncio.run(list_federations(mock_context))

        # Verify console output
        mock_console.print.assert_called()
        print_calls = [call[0][0] for call in mock_console.print.call_args_list]
        assert any("Federation List Command" in str(call) for call in print_calls)
        assert any("Not yet implemented" in str(call) for call in print_calls)


class TestFederationCreate:
    """Test federation create functionality."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock typer context."""
        ctx = Mock(spec=typer.Context)
        ctx.params = {"json_output": False}
        ctx.obj = SimpleNamespace(profile="default", verbose=False, json_output=False)
        return ctx

    @patch("vantage_cli.commands.cluster.federation.create.get_effective_json_output")
    @patch("vantage_cli.commands.cluster.federation.create.print_json")
    def test_create_federation_json_output(
        self, mock_print_json, mock_get_json_output, mock_context
    ):
        """Test create federation with JSON output."""
        mock_get_json_output.return_value = True

        # Run the command
        import asyncio

        asyncio.run(create_federation(mock_context, "test-federation", "Test description"))

        # Verify JSON output was called with expected data
        mock_print_json.assert_called_once()
        call_args = mock_print_json.call_args[1]
        assert "data" in call_args
        assert call_args["data"]["name"] == "test-federation"
        assert call_args["data"]["description"] == "Test description"
        assert call_args["data"]["status"] == "created"

    @patch("vantage_cli.commands.cluster.federation.create.get_effective_json_output")
    @patch("vantage_cli.commands.cluster.federation.create.Console")
    def test_create_federation_console_output(
        self, mock_console_class, mock_get_json_output, mock_context
    ):
        """Test create federation with console output."""
        mock_get_json_output.return_value = False
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        # Run the command
        import asyncio

        asyncio.run(create_federation(mock_context, "test-federation", "Test description"))

        # Verify console output
        mock_console.print.assert_called()
        print_calls = [call[0][0] for call in mock_console.print.call_args_list]
        assert any("Federation Create Command" in str(call) for call in print_calls)
        assert any("test-federation" in str(call) for call in print_calls)

    @patch("vantage_cli.commands.cluster.federation.create.get_effective_json_output")
    @patch("vantage_cli.commands.cluster.federation.create.Console")
    def test_create_federation_no_description(
        self, mock_console_class, mock_get_json_output, mock_context
    ):
        """Test create federation without description."""
        mock_get_json_output.return_value = False
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        # Run the command without description
        import asyncio

        asyncio.run(create_federation(mock_context, "test-federation", ""))

        # Verify console output doesn't include description
        mock_console.print.assert_called()
        print_calls = [call[0][0] for call in mock_console.print.call_args_list]
        assert not any("Description:" in str(call) for call in print_calls)


class TestFederationDelete:
    """Test federation delete functionality."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock typer context."""
        ctx = Mock(spec=typer.Context)
        ctx.params = {"json_output": False}
        ctx.obj = SimpleNamespace(profile="default", verbose=False, json_output=False)
        return ctx

    @patch("vantage_cli.commands.cluster.federation.delete.get_effective_json_output")
    @patch("vantage_cli.commands.cluster.federation.delete.print_json")
    def test_delete_federation_json_output(
        self, mock_print_json, mock_get_json_output, mock_context
    ):
        """Test delete federation with JSON output."""
        mock_get_json_output.return_value = True

        # Run the command with force
        import asyncio

        asyncio.run(delete_federation(mock_context, "test-federation", force=True))

        # Verify JSON output was called with expected data
        mock_print_json.assert_called_once()
        call_args = mock_print_json.call_args[1]
        assert "data" in call_args
        assert call_args["data"]["name"] == "test-federation"
        assert call_args["data"]["force"] is True
        assert call_args["data"]["status"] == "deleted"

    @patch("vantage_cli.commands.cluster.federation.delete.get_effective_json_output")
    @patch("vantage_cli.commands.cluster.federation.delete.Console")
    def test_delete_federation_with_force(
        self, mock_console_class, mock_get_json_output, mock_context
    ):
        """Test delete federation with force flag."""
        mock_get_json_output.return_value = False
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        # Run the command with force
        import asyncio

        asyncio.run(delete_federation(mock_context, "test-federation", force=True))

        # Verify console output
        mock_console.print.assert_called()
        print_calls = [call[0][0] for call in mock_console.print.call_args_list]
        assert any("Federation Delete Command" in str(call) for call in print_calls)
        assert any("test-federation" in str(call) for call in print_calls)
        assert any("Force deletion enabled" in str(call) for call in print_calls)

    @patch("vantage_cli.commands.cluster.federation.delete.get_effective_json_output")
    @patch("vantage_cli.commands.cluster.federation.delete.typer.confirm")
    @patch("vantage_cli.commands.cluster.federation.delete.Console")
    def test_delete_federation_confirmation_cancelled(
        self, mock_console_class, mock_confirm, mock_get_json_output, mock_context
    ):
        """Test delete federation with cancelled confirmation."""
        mock_get_json_output.return_value = False
        mock_confirm.return_value = False  # User cancels
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        # Run the command without force
        import asyncio

        asyncio.run(delete_federation(mock_context, "test-federation", force=False))

        # Verify confirmation was asked and cancellation message shown
        mock_confirm.assert_called_once()
        print_calls = [call[0][0] for call in mock_console.print.call_args_list]
        assert any("Deletion cancelled" in str(call) for call in print_calls)

    @patch("vantage_cli.commands.cluster.federation.delete.get_effective_json_output")
    @patch("vantage_cli.commands.cluster.federation.delete.typer.confirm")
    @patch("vantage_cli.commands.cluster.federation.delete.Console")
    def test_delete_federation_confirmation_accepted(
        self, mock_console_class, mock_confirm, mock_get_json_output, mock_context
    ):
        """Test delete federation with accepted confirmation."""
        mock_get_json_output.return_value = False
        mock_confirm.return_value = True  # User accepts
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        # Run the command without force
        import asyncio

        asyncio.run(delete_federation(mock_context, "test-federation", force=False))

        # Verify confirmation was asked and deletion proceeded
        mock_confirm.assert_called_once()
        print_calls = [call[0][0] for call in mock_console.print.call_args_list]
        assert any("Federation Delete Command" in str(call) for call in print_calls)
        assert any("test-federation" in str(call) for call in print_calls)


class TestFederationGet:
    """Test federation get functionality."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock typer context."""
        ctx = Mock(spec=typer.Context)
        ctx.params = {"json_output": False}
        ctx.obj = SimpleNamespace(profile="default", verbose=False, json_output=False)
        return ctx

    @patch("vantage_cli.commands.cluster.federation.get.get_effective_json_output")
    @patch("vantage_cli.commands.cluster.federation.get.print_json")
    def test_get_federation_json_output(self, mock_print_json, mock_get_json_output, mock_context):
        """Test get federation with JSON output."""
        mock_get_json_output.return_value = True

        # Run the command
        import asyncio

        asyncio.run(get_federation(mock_context, "test-federation"))

        # Verify JSON output was called with expected data
        mock_print_json.assert_called_once()
        call_args = mock_print_json.call_args[1]
        assert "data" in call_args
        assert call_args["data"]["name"] == "test-federation"
        assert call_args["data"]["status"] == "active"
        assert "clusters" in call_args["data"]
        assert "created_at" in call_args["data"]

    @patch("vantage_cli.commands.cluster.federation.get.get_effective_json_output")
    @patch("vantage_cli.commands.cluster.federation.get.Console")
    def test_get_federation_console_output(
        self, mock_console_class, mock_get_json_output, mock_context
    ):
        """Test get federation with console output."""
        mock_get_json_output.return_value = False
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        # Run the command
        import asyncio

        asyncio.run(get_federation(mock_context, "test-federation"))

        # Verify console output
        mock_console.print.assert_called()
        print_calls = [call[0][0] for call in mock_console.print.call_args_list]
        assert any("Federation Get Command" in str(call) for call in print_calls)
        assert any("test-federation" in str(call) for call in print_calls)


class TestFederationUpdate:
    """Test federation update functionality."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock typer context."""
        ctx = Mock(spec=typer.Context)
        ctx.params = {"json_output": False}
        ctx.obj = SimpleNamespace(profile="default", verbose=False, json_output=False)
        return ctx

    @patch("vantage_cli.commands.cluster.federation.update.get_effective_json_output")
    @patch("vantage_cli.commands.cluster.federation.update.print_json")
    def test_update_federation_json_output(
        self, mock_print_json, mock_get_json_output, mock_context
    ):
        """Test update federation with JSON output."""
        mock_get_json_output.return_value = True

        # Run the command with all options
        import asyncio

        mock_context.obj.json_output = True
        asyncio.run(
            update_federation(
                mock_context,
                "test-federation",
                description="New description",
                add_cluster="cluster-1",
                remove_cluster="cluster-2",
            )
        )

        # Verify JSON output was called with expected data
        mock_print_json.assert_called_once()
        call_args = mock_print_json.call_args[1]
        assert "data" in call_args
        assert call_args["data"]["name"] == "test-federation"
        assert call_args["data"]["description"] == "New description"
        assert call_args["data"]["add_cluster"] == "cluster-1"
        assert call_args["data"]["remove_cluster"] == "cluster-2"
        assert call_args["data"]["status"] == "updated"

    @patch("vantage_cli.commands.cluster.federation.update.get_effective_json_output")
    @patch("vantage_cli.commands.cluster.federation.update.Console")
    def test_update_federation_console_output_full(
        self, mock_console_class, mock_get_json_output, mock_context
    ):
        """Test update federation with console output and all options."""
        mock_get_json_output.return_value = False
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        # Run the command with all options
        import asyncio

        mock_context.obj.json_output = False
        asyncio.run(
            update_federation(
                mock_context,
                "test-federation",
                description="New description",
                add_cluster="cluster-1",
                remove_cluster="cluster-2",
            )
        )

        # Verify console output
        mock_console.print.assert_called()
        print_calls = [call[0][0] for call in mock_console.print.call_args_list]
        assert any("Federation Update Command" in str(call) for call in print_calls)
        assert any("test-federation" in str(call) for call in print_calls)
        assert any("New description" in str(call) for call in print_calls)
        assert any("cluster-1" in str(call) for call in print_calls)
        assert any("cluster-2" in str(call) for call in print_calls)

    @patch("vantage_cli.commands.cluster.federation.update.get_effective_json_output")
    @patch("vantage_cli.commands.cluster.federation.update.Console")
    def test_update_federation_console_output_minimal(
        self, mock_console_class, mock_get_json_output, mock_context
    ):
        """Test update federation with console output and minimal options."""
        mock_get_json_output.return_value = False
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        # Run the command with only name
        import asyncio

        asyncio.run(update_federation(mock_context, "test-federation"))

        # Verify console output
        mock_console.print.assert_called()
        print_calls = [call[0][0] for call in mock_console.print.call_args_list]
        assert any("Federation Update Command" in str(call) for call in print_calls)
        assert any("test-federation" in str(call) for call in print_calls)
        # Should not contain description, add_cluster, or remove_cluster
        assert not any("New description" in str(call) for call in print_calls)
        assert not any("Adding cluster" in str(call) for call in print_calls)
        assert not any("Removing cluster" in str(call) for call in print_calls)


class TestFederationCommandStructure:
    """Test federation command app structure."""

    def test_federation_app_is_typer_instance(self):
        """Test that federation_app is a Typer instance."""
        from vantage_cli import AsyncTyper
        from vantage_cli.commands.cluster.federation import federation_app

        assert isinstance(federation_app, AsyncTyper)

    def test_federation_commands_registered(self):
        """Test that all federation commands are registered."""
        from vantage_cli.commands.cluster.federation import federation_app

        # Get all registered commands - it's a list, not dict
        commands = federation_app.registered_commands
        command_names = {cmd.name for cmd in commands}

        # Check that all expected commands are registered
        expected_commands = {"create", "delete", "get", "list", "update"}
        assert command_names == expected_commands

    def test_federation_app_configuration(self):
        """Test federation app configuration."""
        from vantage_cli.commands.cluster.federation import federation_app

        assert federation_app.info.name == "federation"
        assert "federation" in federation_app.info.help.lower()
        assert federation_app.info.no_args_is_help is True
