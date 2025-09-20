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
"""Unit tests for the app list command."""

import types
from unittest.mock import Mock, patch

import pytest
import typer

from vantage_cli.commands.app.list import list_apps
from vantage_cli.render import RenderStepOutput


class MockConsole:
    """Mock Rich Console for testing."""

    def __init__(self):
        self.logged_messages = []
        self.printed_messages = []
        self.tables = []

    def log(self, message: str):
        """Mock log method."""
        self.logged_messages.append(message)

    def print(self, *args, **kwargs):
        """Mock print method."""
        messages = []
        for arg in args:
            if hasattr(arg, "__rich__") or hasattr(arg, "_rows"):
                # This is a Rich object like a Table
                # Extract the text content from Rich table rows
                if hasattr(arg, "_rows"):
                    for row in arg._rows:
                        if hasattr(row, "_cells"):
                            for cell in row._cells:
                                messages.append(str(cell))
                        else:
                            # Handle different row structures
                            messages.extend(str(cell) for cell in row if cell)
                messages.append("[Table rendered]")
            else:
                messages.append(str(arg))

        message = " ".join(messages)
        self.printed_messages.append(message)

    def clear(self):
        """Clear all stored messages."""
        self.logged_messages.clear()
        self.printed_messages.clear()
        self.tables.clear()

    def set_live(self, live):
        """Mock set_live method."""
        pass


def create_mock_deploy_function(description: str):
    """Create a mock deploy function with a docstring."""

    def mock_deploy():
        pass

    mock_deploy.__doc__ = description
    return mock_deploy


def create_mock_module(name: str):
    """Create a mock module with a specific name."""
    module = types.ModuleType(name)
    module.__name__ = name
    return module


@pytest.fixture
def mock_context():
    """Create a mock typer Context for testing."""
    context = Mock(spec=typer.Context)

    # Create mock obj with necessary attributes
    obj = Mock()
    obj.console = MockConsole()
    obj.json_output = False
    obj.verbose = False
    obj.command_start_time = 1234567890.0

    context.obj = obj
    return context


@pytest.fixture
def sample_apps():
    """Sample apps data for testing."""
    return {
        "slurm-microk8s-localhost": {
            "module": create_mock_module("vantage_cli.apps.slurm_microk8s_localhost.app"),
            "deploy_function": create_mock_deploy_function(
                "Deploy SLURM cluster on MicroK8s using Helm."
            ),
        },
        "jupyterhub-microk8s-localhost": {
            "module": create_mock_module("vantage_cli.apps.jupyterhub_microk8s_localhost.app"),
            "deploy_function": create_mock_deploy_function(
                "Deploy JupyterHub on MicroK8s for cluster management."
            ),
        },
        "keycloak-microk8s-localhost": {
            "module": create_mock_module("vantage_cli.apps.keycloak_microk8s_localhost.app"),
            "deploy_function": create_mock_deploy_function("Deploy Keycloak on MicroK8s."),
        },
    }


class TestListApps:
    """Test cases for the list_apps function."""

    @pytest.mark.asyncio
    async def test_list_apps_normal_output(self, mock_context, sample_apps):
        """Test normal table output format."""
        with patch("vantage_cli.commands.app.list.get_available_apps", return_value=sample_apps):
            with patch("vantage_cli.commands.app.list.RenderStepOutput") as mock_render:
                # Setup mock renderer
                mock_renderer_instance = Mock()
                mock_render.return_value = mock_renderer_instance
                mock_renderer_instance.__enter__ = Mock(return_value=mock_renderer_instance)
                mock_renderer_instance.__exit__ = Mock(return_value=None)

                await list_apps(mock_context)

                # Verify console interactions
                console = mock_context.obj.console

                # Check that table was printed (Rich table objects are passed to print)
                printed_text = " ".join(console.printed_messages)
                # The Rich Table object itself gets printed, which shows it was created and displayed
                assert "Table" in printed_text  # Rich table object reference
                # Verify the render system was used (which would contain the actual data)

                # Check that summary was printed
                assert any("Found 3 application(s)" in msg for msg in console.printed_messages)

                # Verify RenderStepOutput was used correctly
                mock_render.assert_called_once()
                mock_renderer_instance.complete_step.assert_called()
                mock_renderer_instance.start_step.assert_called()

    @pytest.mark.asyncio
    async def test_list_apps_json_output(self, mock_context, sample_apps):
        """Test JSON output format."""
        mock_context.obj.json_output = True

        with patch("vantage_cli.commands.app.list.get_available_apps", return_value=sample_apps):
            with patch.object(RenderStepOutput, "json_bypass") as mock_json_bypass:
                await list_apps(mock_context)

                # Verify JSON output was called
                mock_json_bypass.assert_called_once()

                # Get the JSON data that was passed
                json_data = mock_json_bypass.call_args[0][0]

                # Verify structure
                assert "apps" in json_data
                assert len(json_data["apps"]) == 3

                # Verify each app has required fields
                for app in json_data["apps"]:
                    assert "name" in app
                    assert "module" in app
                    assert "description" in app

                # Verify specific app data
                app_names = [app["name"] for app in json_data["apps"]]
                assert "slurm-microk8s-localhost" in app_names
                assert "jupyterhub-microk8s-localhost" in app_names
                assert "keycloak-microk8s-localhost" in app_names

                # Verify descriptions are extracted from docstrings
                slurm_app = next(
                    app for app in json_data["apps"] if app["name"] == "slurm-microk8s-localhost"
                )
                assert "Deploy SLURM cluster on MicroK8s using Helm." in slurm_app["description"]

    @pytest.mark.asyncio
    async def test_list_apps_empty_result(self, mock_context):
        """Test behavior when no apps are found."""
        with patch("vantage_cli.commands.app.list.get_available_apps", return_value={}):
            with patch("vantage_cli.commands.app.list.RenderStepOutput") as mock_render:
                mock_renderer_instance = Mock()
                mock_render.return_value = mock_renderer_instance
                mock_renderer_instance.__enter__ = Mock(return_value=mock_renderer_instance)
                mock_renderer_instance.__exit__ = Mock(return_value=None)

                await list_apps(mock_context)

                # Verify console interactions
                console = mock_context.obj.console

                # Check empty result handling
                pass  # No discovery logging expected anymore

                # Check that "no applications found" message was printed
                assert any("No applications found" in msg for msg in console.printed_messages)

    @pytest.mark.asyncio
    async def test_list_apps_empty_json_output(self, mock_context):
        """Test JSON output when no apps are found."""
        mock_context.obj.json_output = True

        with patch("vantage_cli.commands.app.list.get_available_apps", return_value={}):
            with patch.object(RenderStepOutput, "json_bypass") as mock_json_bypass:
                await list_apps(mock_context)

                # Verify JSON output was called
                mock_json_bypass.assert_called_once()

                # Get the JSON data that was passed
                json_data = mock_json_bypass.call_args[0][0]

                # Verify structure
                assert "apps" in json_data
                assert len(json_data["apps"]) == 0

    @pytest.mark.asyncio
    async def test_list_apps_verbose_mode(self, mock_context, sample_apps):
        """Test verbose mode."""
        mock_context.obj.verbose = True

        with patch("vantage_cli.commands.app.list.get_available_apps", return_value=sample_apps):
            with patch("vantage_cli.commands.app.list.RenderStepOutput") as mock_render:
                mock_renderer_instance = Mock()
                mock_render.return_value = mock_renderer_instance
                mock_renderer_instance.__enter__ = Mock(return_value=mock_renderer_instance)
                mock_renderer_instance.__exit__ = Mock(return_value=None)

                await list_apps(mock_context)

                # Verify RenderStepOutput was initialized with verbose=True
                args, kwargs = mock_render.call_args
                assert kwargs.get("verbose") is True

    @pytest.mark.asyncio
    async def test_list_apps_missing_deploy_function(self, mock_context):
        """Test behavior when app has no deploy function."""
        apps_without_deploy = {
            "broken-app": {
                "module": create_mock_module("vantage_cli.apps.broken_app.app"),
                # Missing deploy_function
            }
        }

        with patch(
            "vantage_cli.commands.app.list.get_available_apps", return_value=apps_without_deploy
        ):
            with patch.object(RenderStepOutput, "json_bypass") as mock_json_bypass:
                mock_context.obj.json_output = True

                await list_apps(mock_context)

                # Get the JSON data
                json_data = mock_json_bypass.call_args[0][0]

                # Verify the app shows appropriate message for missing deploy function
                app = json_data["apps"][0]
                assert app["name"] == "broken-app"
                assert app["description"] == "No deploy function available"

    @pytest.mark.asyncio
    async def test_list_apps_missing_docstring(self, mock_context):
        """Test behavior when deploy function has no docstring."""

        def deploy_without_docstring():
            pass

        # Explicitly set no docstring
        deploy_without_docstring.__doc__ = None

        apps_no_docstring = {
            "no-doc-app": {
                "module": create_mock_module("vantage_cli.apps.no_doc_app.app"),
                "deploy_function": deploy_without_docstring,
            }
        }

        with patch(
            "vantage_cli.commands.app.list.get_available_apps", return_value=apps_no_docstring
        ):
            with patch.object(RenderStepOutput, "json_bypass") as mock_json_bypass:
                mock_context.obj.json_output = True

                await list_apps(mock_context)

                # Get the JSON data
                json_data = mock_json_bypass.call_args[0][0]

                # Verify the app shows appropriate message for missing docstring
                app = json_data["apps"][0]
                assert app["name"] == "no-doc-app"
                assert app["description"] == "No description available"

    @pytest.mark.asyncio
    async def test_list_apps_multiline_docstring(self, mock_context):
        """Test that only first line of docstring is used."""
        multiline_deploy = create_mock_deploy_function(
            "Deploy complex application.\n\nThis is a detailed description\nwith multiple lines."
        )

        multiline_apps = {
            "multiline-app": {
                "module": create_mock_module("vantage_cli.apps.multiline_app.app"),
                "deploy_function": multiline_deploy,
            }
        }

        with patch(
            "vantage_cli.commands.app.list.get_available_apps", return_value=multiline_apps
        ):
            with patch.object(RenderStepOutput, "json_bypass") as mock_json_bypass:
                mock_context.obj.json_output = True

                await list_apps(mock_context)

                # Get the JSON data
                json_data = mock_json_bypass.call_args[0][0]

                # Verify only first line is used
                app = json_data["apps"][0]
                assert app["description"] == "Deploy complex application."

    @pytest.mark.asyncio
    async def test_list_apps_missing_module_name(self, mock_context):
        """Test behavior when module has no __name__ attribute."""
        broken_module = Mock()
        # Remove __name__ attribute
        del broken_module.__name__

        broken_apps = {
            "broken-module-app": {
                "module": broken_module,
                "deploy_function": create_mock_deploy_function("Test app"),
            }
        }

        with patch("vantage_cli.commands.app.list.get_available_apps", return_value=broken_apps):
            with patch.object(RenderStepOutput, "json_bypass") as mock_json_bypass:
                mock_context.obj.json_output = True

                await list_apps(mock_context)

                # Get the JSON data
                json_data = mock_json_bypass.call_args[0][0]

                # Verify unknown module name is handled
                app = json_data["apps"][0]
                assert app["module"] == "unknown"

    @pytest.mark.asyncio
    async def test_list_apps_exception_handling(self, mock_context):
        """Test exception handling in list_apps."""
        with patch(
            "vantage_cli.commands.app.list.get_available_apps", side_effect=Exception("Test error")
        ):
            with pytest.raises(typer.Exit) as exc_info:
                await list_apps(mock_context)

            # Verify exit code
            assert exc_info.value.exit_code == 1

            # Verify error message was printed
            console = mock_context.obj.console
            assert any(
                "Error listing applications: Test error" in msg for msg in console.printed_messages
            )

    @pytest.mark.asyncio
    async def test_context_attributes_access(self, mock_context, sample_apps):
        """Test that context attributes are properly accessed."""
        # Test with missing attributes (should default gracefully)
        mock_context.obj.json_output = None
        mock_context.obj.verbose = None

        with patch("vantage_cli.commands.app.list.get_available_apps", return_value=sample_apps):
            with patch("vantage_cli.commands.app.list.RenderStepOutput") as mock_render:
                mock_renderer_instance = Mock()
                mock_render.return_value = mock_renderer_instance
                mock_renderer_instance.__enter__ = Mock(return_value=mock_renderer_instance)
                mock_renderer_instance.__exit__ = Mock(return_value=None)

                await list_apps(mock_context)

                # Should not crash and should use table output (default behavior)
                mock_render.assert_called_once()
