"""Tests for the apps list command."""

import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
import typer

from vantage_cli.commands.app.list import list_apps


@pytest.fixture
def mock_config_file():
    """Mock config file for @attach_settings decorator."""
    with patch("vantage_cli.config.USER_CONFIG_FILE") as mock_config_file:
        mock_config_file.exists.return_value = True
        mock_config_file.read_text.return_value = json.dumps(
            {"default": {"api_base_url": "https://test.com"}}
        )
        yield mock_config_file


@pytest.fixture
def mock_ctx() -> typer.Context:
    """Mock typer context."""
    ctx = Mock(spec=typer.Context)
    # Mock the obj attribute with profile for @attach_settings decorator
    ctx.obj = SimpleNamespace(profile="default", verbose=False, json_output=False)
    return ctx


@pytest.fixture
def mock_console():
    """Mock rich console."""
    with patch("vantage_cli.commands.app.list.console") as mock_console:
        yield mock_console


@pytest.fixture
def mock_available_apps():
    """Mock available apps data."""

    def mock_deploy_func_with_docstring():
        """Deploy a test application."""
        pass

    def mock_deploy_func_without_docstring():
        pass

    mock_module_1 = Mock()
    mock_module_1.__name__ = "vantage_cli.apps.test_app1"
    mock_module_1.deploy = mock_deploy_func_with_docstring

    mock_module_2 = Mock()
    mock_module_2.__name__ = "vantage_cli.apps.test_app2"
    mock_module_2.deploy = mock_deploy_func_without_docstring

    return {
        "test-app-1": {
            "module": mock_module_1,
            "deploy_function": mock_deploy_func_with_docstring,
        },
        "test-app-2": {
            "module": mock_module_2,
            "deploy_function": mock_deploy_func_without_docstring,
        },
    }


class TestListApps:
    """Tests for the list_apps function."""

    @patch("vantage_cli.commands.app.list.get_available_apps")
    @patch("vantage_cli.commands.app.list.render_json")
    @pytest.mark.asyncio
    async def test_list_apps_json_output_with_apps(
        self,
        mock_render_json,
        mock_get_available_apps,
        mock_config_file,
        mock_ctx,
        mock_available_apps,
    ):
        """Test list_apps command with JSON output and available apps."""
        mock_get_available_apps.return_value = mock_available_apps
        mock_ctx.obj.json_output = True
        await list_apps(mock_ctx)

        # Verify render_json was called with the correct structure
        mock_render_json.assert_called_once()
        call_args = mock_render_json.call_args[0][0]

        assert "apps" in call_args
        assert len(call_args["apps"]) == 2

        # Check first app
        app1 = call_args["apps"][0]
        assert app1["name"] == "test-app-1"
        assert app1["module"] == "vantage_cli.apps.test_app1"
        assert app1["description"] == "Deploy a test application."

        # Check second app
        app2 = call_args["apps"][1]
        assert app2["name"] == "test-app-2"
        assert app2["module"] == "vantage_cli.apps.test_app2"
        assert app2["description"] == "No description available"

    @patch("vantage_cli.commands.app.list.get_available_apps")
    @patch("vantage_cli.commands.app.list.render_json")
    @pytest.mark.asyncio
    async def test_list_apps_json_output_empty(
        self, mock_render_json, mock_get_available_apps, mock_config_file, mock_ctx
    ):
        """Test list_apps with JSON output when no apps are available."""
        mock_get_available_apps.return_value = {}
        mock_ctx.obj.json_output = True
        await list_apps(mock_ctx)

        # Verify render_json was called with empty apps list
        mock_render_json.assert_called_once_with({"apps": []})

    @patch("vantage_cli.commands.app.list.get_available_apps")
    @pytest.mark.asyncio
    async def test_list_apps_table_output_with_apps(
        self,
        mock_get_available_apps,
        mock_config_file,
        mock_ctx,
        mock_console,
        mock_available_apps,
    ):
        """Test list_apps with table output when apps are available."""
        mock_get_available_apps.return_value = mock_available_apps
        mock_ctx.obj.json_output = False
        await list_apps(mock_ctx)

        # Verify console.print was called (for the table and summary)
        assert mock_console.print.call_count == 2

        # Check that the summary message was printed
        summary_call = mock_console.print.call_args_list[1]
        assert "Found 2 application(s)" in str(summary_call)

    @patch("vantage_cli.commands.app.list.get_available_apps")
    @pytest.mark.asyncio
    async def test_list_apps_table_output_empty(
        self, mock_get_available_apps, mock_config_file, mock_ctx, mock_console
    ):
        """Test list_apps with table output when no apps are available."""
        mock_get_available_apps.return_value = {}
        mock_ctx.obj.json_output = False
        await list_apps(mock_ctx)

        # Verify console.print was called with "No applications found"
        mock_console.print.assert_called_once_with("[yellow]No applications found.[/yellow]")

    @patch("vantage_cli.commands.app.list.get_available_apps")
    @pytest.mark.asyncio
    async def test_list_apps_app_with_no_module_name(
        self, mock_get_available_apps, mock_config_file, mock_ctx, mock_console
    ):
        """Test list_apps handles apps with modules without __name__ attribute."""
        mock_module = Mock()
        del mock_module.__name__  # Remove __name__ attribute

        def mock_deploy_func():
            """Deploy function."""
            pass

        mock_apps = {
            "test-app": {
                "module": mock_module,
                "deploy_function": mock_deploy_func,
            },
        }
        mock_get_available_apps.return_value = mock_apps
        mock_ctx.obj.json_output = False
        await list_apps(mock_ctx)

        # Should handle the missing __name__ gracefully
        assert mock_console.print.call_count == 2

    @patch("vantage_cli.commands.app.list.get_available_apps")
    @pytest.mark.asyncio
    async def test_list_apps_app_without_deploy_function(
        self, mock_get_available_apps, mock_config_file, mock_ctx, mock_console
    ):
        """Test list_apps handles apps without deploy function."""
        mock_module = Mock()
        mock_module.__name__ = "test.module"

        mock_apps = {
            "test-app": {
                "module": mock_module,
                # No deploy_function key
            },
        }
        mock_get_available_apps.return_value = mock_apps
        mock_ctx.obj.json_output = False
        await list_apps(mock_ctx)

        # Should handle the missing deploy_function gracefully
        assert mock_console.print.call_count == 2

    @patch("vantage_cli.commands.app.list.get_available_apps")
    @pytest.mark.asyncio
    async def test_list_apps_json_output_handles_missing_attributes(
        self, mock_get_available_apps, mock_config_file, mock_ctx
    ):
        """Test list_apps JSON output handles missing module/function attributes."""
        with patch("vantage_cli.commands.app.list.render_json") as mock_render_json:
            mock_module = Mock()
            del mock_module.__name__  # Remove __name__ attribute

            mock_apps = {
                "test-app": {
                    "module": mock_module,
                    # No deploy_function key
                },
            }
            mock_get_available_apps.return_value = mock_apps
            mock_ctx.obj.json_output = True
            await list_apps(mock_ctx)

            # Verify render_json was called with fallback values
            mock_render_json.assert_called_once()
            call_args = mock_render_json.call_args[0][0]

            assert "apps" in call_args
            assert len(call_args["apps"]) == 1

            app = call_args["apps"][0]
            assert app["name"] == "test-app"
            assert app["module"] == "unknown"
            assert app["description"] == "No deploy function available"

    @patch("vantage_cli.commands.app.list.get_available_apps")
    @pytest.mark.asyncio
    async def test_list_apps_handles_exception(
        self, mock_get_available_apps, mock_config_file, mock_ctx, mock_console
    ):
        """Test list_apps handles exceptions gracefully."""
        mock_get_available_apps.side_effect = Exception("Test error")
        mock_ctx.obj.json_output = False
        with pytest.raises(typer.Exit) as exc_info:
            await list_apps(mock_ctx)

        # Verify it exits with code 1
        assert exc_info.value.exit_code == 1

        # Verify error message was printed
        mock_console.print.assert_called_once()
        error_call = mock_console.print.call_args[0][0]
        assert "Error listing applications: Test error" in error_call

    @patch("vantage_cli.commands.app.list.get_available_apps")
    @pytest.mark.asyncio
    async def test_list_apps_multiline_docstring(
        self, mock_get_available_apps, mock_config_file, mock_ctx, mock_console
    ):
        """Test list_apps handles multiline docstrings correctly."""

        def mock_deploy_func():
            """Deploy a complex application.

            This is a more detailed description
            that spans multiple lines.
            """
            pass

        mock_module = Mock()
        mock_module.__name__ = "vantage_cli.apps.complex_app"

        mock_apps = {
            "complex-app": {
                "module": mock_module,
                "deploy_function": mock_deploy_func,
            },
        }
        mock_get_available_apps.return_value = mock_apps
        mock_ctx.obj.json_output = False
        await list_apps(mock_ctx)

        # Should use only the first line of the docstring
        assert mock_console.print.call_count == 2

    @patch("vantage_cli.commands.app.list.get_available_apps")
    @patch("vantage_cli.commands.app.list.render_json")
    @pytest.mark.asyncio
    async def test_list_apps_json_multiline_docstring(
        self, mock_render_json, mock_get_available_apps, mock_config_file, mock_ctx
    ):
        """Test list_apps JSON output handles multiline docstrings correctly."""

        def mock_deploy_func():
            """Deploy a complex application.

            This is a more detailed description.
            """
            pass

        mock_module = Mock()
        mock_module.__name__ = "vantage_cli.apps.complex_app"

        mock_apps = {
            "complex-app": {
                "module": mock_module,
                "deploy_function": mock_deploy_func,
            },
        }
        mock_get_available_apps.return_value = mock_apps
        mock_ctx.obj.json_output = True
        await list_apps(mock_ctx)

        # Verify render_json was called with first line of docstring
        mock_render_json.assert_called_once()
        call_args = mock_render_json.call_args[0][0]

        app = call_args["apps"][0]
        assert app["description"] == "Deploy a complex application."
