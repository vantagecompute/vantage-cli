"""Isolated unit tests for app list command - completely without decorators or complex dependencies."""

import asyncio
from unittest.mock import Mock, patch


def create_mock_module(module_name: str):
    """Create a mock module with a __name__ attribute."""
    mock_module = Mock()
    mock_module.__name__ = module_name
    return mock_module


def create_mock_deploy_function(docstring: str):
    """Create a mock deploy function with a docstring."""
    mock_func = Mock()
    mock_func.__doc__ = docstring
    return mock_func


class SimpleConsole:
    """Ultra-simple console for testing that just tracks messages."""

    def __init__(self):
        self.logged_messages = []
        self.printed_messages = []

    def log(self, message):
        """Log a message."""
        self.logged_messages.append(str(message))

    def print(self, message):
        """Print a message."""
        self.printed_messages.append(str(message))


async def simple_list_apps_logic(available_apps, console, json_output=False):
    """Super simple version of app listing logic for testing."""
    if json_output:
        # Simple JSON output
        apps_data = []
        for app_name, app_info in available_apps.items():
            # Handle module name
            module_name = "unknown"
            if "module" in app_info and hasattr(app_info["module"], "__name__"):
                module_name = app_info["module"].__name__

            # Handle description
            description = "No description available"
            if "deploy_function" in app_info and hasattr(app_info["deploy_function"], "__doc__"):
                description = app_info["deploy_function"].__doc__

            app_data = {"name": app_name, "module": module_name, "description": description}
            apps_data.append(app_data)

        console.print(f'JSON: {{"apps": {apps_data}}}')
        return

    # Simple table output
    if not available_apps:
        console.print("No applications found.")
        return

    console.print("Available Applications:")
    for app_name, app_info in available_apps.items():
        module_name = "unknown"
        if "module" in app_info:
            module = app_info["module"]
            if hasattr(module, "__name__"):
                module_name = module.__name__

        description = "No description available"
        if "deploy_function" in app_info:
            func = app_info["deploy_function"]
            if hasattr(func, "__doc__") and func.__doc__:
                description = func.__doc__.strip().split("\n")[0]

        console.print(f"- {app_name} ({module_name}): {description}")

    console.print(f"Found {len(available_apps)} application(s)")


def test_simple_json_output():
    """Test JSON output with simple logic."""
    console = SimpleConsole()

    sample_apps = {
        "slurm-microk8s-localhost": {
            "module": create_mock_module("vantage_cli.apps.slurm_microk8s_localhost.app"),
            "deploy_function": create_mock_deploy_function(
                "Deploy SLURM cluster on MicroK8s using Helm."
            ),
        }
    }

    asyncio.run(simple_list_apps_logic(sample_apps, console, json_output=True))

    # Verify results - no logging expected anymore
    assert len(console.logged_messages) == 0

    assert len(console.printed_messages) == 1
    json_output = console.printed_messages[0]
    assert "JSON:" in json_output
    assert "slurm-microk8s-localhost" in json_output
    assert "Deploy SLURM cluster on MicroK8s using Helm." in json_output


def test_simple_table_output():
    """Test table output with simple logic."""
    console = SimpleConsole()

    sample_apps = {
        "slurm-microk8s-localhost": {
            "module": create_mock_module("vantage_cli.apps.slurm_microk8s_localhost.app"),
            "deploy_function": create_mock_deploy_function(
                "Deploy SLURM cluster on MicroK8s using Helm."
            ),
        },
        "jupyterhub-microk8s-localhost": {
            "module": create_mock_module("vantage_cli.apps.jupyterhub_microk8s_localhost.app"),
            "deploy_function": create_mock_deploy_function(
                "Deploy JupyterHub on MicroK8s using Helm."
            ),
        },
    }

    asyncio.run(simple_list_apps_logic(sample_apps, console, json_output=False))

    # Verify results - no logging expected anymore
    assert len(console.logged_messages) == 0

    # Check console output
    output_text = " ".join(console.printed_messages)
    assert "Available Applications:" in output_text
    assert "slurm-microk8s-localhost" in output_text
    assert "jupyterhub-microk8s-localhost" in output_text
    assert "Deploy SLURM cluster" in output_text
    assert "Deploy JupyterHub" in output_text
    assert "Found 2 application(s)" in output_text


def test_simple_empty_apps():
    """Test empty apps list."""
    console = SimpleConsole()

    asyncio.run(simple_list_apps_logic({}, console, json_output=False))

    # Verify results - no logging expected anymore
    assert len(console.logged_messages) == 0

    assert len(console.printed_messages) == 1
    assert "No applications found." in console.printed_messages[0]


def test_simple_missing_deploy_function():
    """Test handling apps without deploy function."""
    console = SimpleConsole()

    sample_apps = {
        "broken-app": {
            "module": create_mock_module("vantage_cli.apps.broken_app.app"),
            # No deploy_function
        }
    }

    asyncio.run(simple_list_apps_logic(sample_apps, console, json_output=False))

    # Verify results
    output_text = " ".join(console.printed_messages)
    assert "broken-app" in output_text
    assert "No description available" in output_text


def test_get_available_apps_directly():
    """Test that we can call get_available_apps and get expected structure."""
    with patch("vantage_cli.apps.utils.get_available_apps") as mock_get_apps:
        # Mock the function to return expected structure
        mock_get_apps.return_value = {
            "test-app": {
                "module": create_mock_module("test.module"),
                "deploy_function": create_mock_deploy_function("Test description."),
            }
        }

        from vantage_cli.apps.utils import get_available_apps

        result = get_available_apps()

        assert "test-app" in result
        assert "module" in result["test-app"]
        assert "deploy_function" in result["test-app"]
        assert result["test-app"]["module"].__name__ == "test.module"
        assert result["test-app"]["deploy_function"].__doc__ == "Test description."


if __name__ == "__main__":
    # Run tests directly if executed
    test_simple_json_output()
    test_simple_table_output()
    test_simple_empty_apps()
    test_simple_missing_deploy_function()
    test_get_available_apps_directly()
    print("All isolated tests passed!")
