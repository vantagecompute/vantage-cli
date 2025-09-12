"""Additional comprehensive tests for apps functionality to increase test coverage.

This module contains systematic test coverage for apps functionality,
focusing on edge cases and error conditions not covered by basic tests.
"""

import subprocess
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, Mock, patch

import pytest
import typer

from vantage_cli.apps.slurm_microk8s_localhost import app as microk8s_app
from vantage_cli.apps.slurm_multipass_localhost import app as multipass_app
from vantage_cli.commands.cluster.utils import get_available_apps


@pytest.fixture
def mock_config_file():
    """Mock config file for @attach_settings decorator."""
    with patch("vantage_cli.config.USER_CONFIG_FILE") as mock_config_file:
        mock_config_file.exists.return_value = True
        yield mock_config_file


@pytest.fixture
def mock_ctx():
    """Mock typer context with settings."""
    ctx = SimpleNamespace()
    ctx.obj = SimpleNamespace()
    ctx.obj.settings = SimpleNamespace()
    ctx.obj.settings.api_base_url = "https://api.example.com"
    ctx.obj.settings.oidc_base_url = "https://auth.example.com"
    ctx.obj.settings.oidc_domain = "auth.example.com"
    ctx.obj.settings.tunnel_api_url = "https://tunnel.example.com"
    return ctx


class TestMicrok8sAppAdditionalCoverage:
    """Additional tests for microk8s app to increase coverage."""

    def test_deploy_file_not_found_error(self, mock_config_file, mock_ctx):
        """Test deploy function handles missing binary gracefully."""
        with patch("shutil.which", return_value=None):
            with pytest.raises(typer.Exit) as exc_info:
                import asyncio

                asyncio.run(microk8s_app.deploy(mock_ctx))

            assert exc_info.value.exit_code == 1

    def test_deploy_with_cluster_data_validation(self, mock_config_file, mock_ctx):
        """Test microk8s deploy with cluster data validation."""
        cluster_data = {
            "name": "test-cluster",
            "clientId": "test-client",
            "clientSecret": "test-secret",
            "creationParameters": {"cloud": "localhost"},
        }

        def mock_run(*args, **kwargs):
            return subprocess.CompletedProcess(args[0], 0, stdout="success")

        with patch("subprocess.run", side_effect=mock_run):
            with patch("shutil.which", return_value="/usr/bin/microk8s"):
                with patch(
                    "vantage_cli.apps.slurm_microk8s_localhost.app.validate_cluster_data",
                    return_value=cluster_data,
                ) as mock_validate_cluster:
                    with patch(
                        "vantage_cli.apps.slurm_microk8s_localhost.app.validate_client_credentials",
                        return_value=("test-client", "test-secret"),
                    ) as mock_validate_creds:
                        with patch(
                            "vantage_cli.commands.cluster.utils.get_cluster_client_secret",
                            new_callable=AsyncMock,
                            return_value="test-secret",
                        ):
                            import asyncio

                            asyncio.run(microk8s_app.deploy(mock_ctx, cluster_data=cluster_data))

                            # Verify validation functions were called
                            mock_validate_cluster.assert_called_once_with(cluster_data, ANY)
                            mock_validate_creds.assert_called_once_with(cluster_data, ANY)

    def test_run_function_with_custom_env(self):
        """Test _run function with custom environment."""
        from rich.console import Console

        from vantage_cli.apps.slurm_microk8s_localhost.app import _run

        custom_env = {"TEST_VAR": "test_value"}

        with patch("subprocess.run") as mock_run:
            expected_result = subprocess.CompletedProcess(["echo", "test"], 0, stdout="success")
            mock_run.return_value = expected_result

            console = Console()
            result = _run(["echo", "test"], console, env=custom_env)

            assert result == expected_result
            mock_run.assert_called_once()

    def test_run_function_file_not_found_allow_fail(self):
        """Test _run function handles FileNotFoundError when allow_fail=True."""
        from rich.console import Console

        from vantage_cli.apps.slurm_microk8s_localhost.app import _run

        with patch("subprocess.run", side_effect=FileNotFoundError("Command not found")):
            console = Console()

            # Should not raise when allow_fail=True, returns CompletedProcess with code 127
            result = _run(["missing-cmd"], console, allow_fail=True)
            assert result.returncode == 127

    def test_run_function_command_failure_no_allow_fail(self):
        """Test _run function handles command failure when allow_fail=False."""
        from rich.console import Console

        from vantage_cli.apps.slurm_microk8s_localhost.app import _run

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                ["false"], 1, stdout="", stderr="failed"
            )

            console = Console()

            with pytest.raises(typer.Exit) as exc_info:
                _run(["false"], console, allow_fail=False)

            assert exc_info.value.exit_code == 1


class TestMultipassAppAdditionalCoverage:
    """Additional tests for multipass app to increase coverage."""

    def test_deploy_command_with_missing_binary(self, mock_config_file, mock_ctx):
        """Test multipass deploy handles missing binary."""
        with patch("shutil.which", return_value=None):
            import click

            with pytest.raises((typer.Exit, click.exceptions.Exit)) as exc_info:
                import asyncio

                asyncio.run(multipass_app.deploy(mock_ctx))

            # Handle both typer.Exit and click.exceptions.Exit
            if hasattr(exc_info.value, "exit_code"):
                assert exc_info.value.exit_code == 1
            else:
                assert exc_info.value.code == 1

    def test_deploy_with_cluster_validation(self, mock_config_file, mock_ctx):
        """Test multipass deploy with cluster data validation."""
        cluster_data = {
            "name": "test-cluster",
            "clientId": "test-client",
            "clientSecret": "test-secret",
        }

        # Mock Popen to simulate successful multipass launch
        mock_popen = Mock()
        mock_popen.returncode = 0
        mock_popen.communicate.return_value = ("", "")

        with patch("subprocess.Popen", return_value=mock_popen):
            with patch(
                "vantage_cli.apps.slurm_multipass_localhost.app.which",
                return_value="/usr/bin/multipass",
            ):
                # Mock at both the app level and the common level to handle import differences
                with patch(
                    "vantage_cli.apps.slurm_multipass_localhost.app.validate_cluster_data",
                    return_value=cluster_data,
                ) as mock_validate_cluster:
                    with patch(
                        "vantage_cli.apps.slurm_multipass_localhost.app.validate_client_credentials",
                        return_value=("test-client", "test-secret"),
                    ) as mock_validate_creds:
                        with patch(
                            "vantage_cli.apps.common.validate_cluster_data",
                            return_value=cluster_data,
                        ):
                            with patch(
                                "vantage_cli.apps.common.validate_client_credentials",
                                return_value=("test-client", "test-secret"),
                            ):
                                with patch(
                                    "vantage_cli.commands.cluster.utils.get_cluster_client_secret",
                                    new_callable=AsyncMock,
                                    return_value="test-secret",
                                ):
                                    with patch(
                                        "vantage_cli.apps.templates.CloudInitTemplate.generate_multipass_config",
                                        return_value="mock-config",
                                    ):
                                        import asyncio

                                        asyncio.run(
                                            multipass_app.deploy(
                                                mock_ctx, cluster_data=cluster_data
                                            )
                                        )

                                        # Verify validation was called
                                        mock_validate_cluster.assert_called_once_with(
                                            cluster_data, ANY
                                        )
                                        mock_validate_creds.assert_called_once_with(
                                            cluster_data, ANY
                                        )

    def test_deploy_subprocess_failure(self, mock_config_file, mock_ctx):
        """Test multipass deploy handles subprocess failure."""
        cluster_data = {
            "name": "test-cluster",
            "clientId": "test-client",
            "clientSecret": "test-secret",
        }

        # Mock Popen to simulate a process failure with return code 5
        mock_popen = Mock()
        mock_popen.returncode = 5
        mock_popen.communicate.return_value = ("", "")

        with patch("subprocess.Popen", return_value=mock_popen):
            with patch("shutil.which", return_value="/usr/bin/multipass"):
                with patch(
                    "vantage_cli.apps.slurm_multipass_localhost.app.validate_cluster_data",
                    return_value=cluster_data,
                ):
                    with patch(
                        "vantage_cli.apps.slurm_multipass_localhost.app.validate_client_credentials",
                        return_value=("test-client", "test-secret"),
                    ):
                        with patch(
                            "vantage_cli.commands.cluster.utils.get_cluster_client_secret",
                            new_callable=AsyncMock,
                            return_value="test-secret",
                        ):
                            with patch(
                                "vantage_cli.apps.templates.CloudInitTemplate.generate_multipass_config",
                                return_value="mock-config",
                            ):
                                import asyncio

                                with pytest.raises(typer.Exit) as exc_info:
                                    asyncio.run(
                                        multipass_app.deploy(mock_ctx, cluster_data=cluster_data)
                                    )

                                assert (
                                    exc_info.value.exit_code == 1
                                )  # The multipass app always exits with code 1 on failure


class TestAppsUtilsCoverage:
    """Tests for apps utility functions to increase coverage."""

    def test_get_available_apps_discovery(self):
        """Test get_available_apps correctly discovers apps."""
        apps = get_available_apps()

        # Should find the three SLURM apps we have
        assert "slurm-juju-localhost" in apps
        assert "slurm-microk8s-localhost" in apps
        assert "slurm-multipass-localhost" in apps

        # Each app should have the required attributes
        for app_name, app_info in apps.items():
            assert "module" in app_info
            assert "deploy_function" in app_info

    def test_get_available_apps_module_loading(self):
        """Test get_available_apps handles module loading correctly."""
        # Test uses real app discovery, so just verify basic functionality
        apps = get_available_apps()

        # Should find real apps and have correct structure
        assert len(apps) >= 3
        for app_name, app_info in apps.items():
            assert callable(app_info["deploy_function"])
            assert hasattr(app_info["module"], "deploy")

    def test_get_available_apps_handles_import_errors(self):
        """Test get_available_apps handles import errors gracefully."""
        # Create a mock broken module path by patching glob to return a fake directory
        fake_path = Mock()
        fake_path.name = "broken-app"
        fake_path.is_dir.return_value = True

        # Mock import_module to raise an ImportError for our fake module
        original_import = __import__

        def mock_import(name, *args, **kwargs):
            if "broken-app" in name:
                raise ImportError("Broken module")
            return original_import(name, *args, **kwargs)

        with (
            patch("pathlib.Path.glob", return_value=[fake_path]),
            patch("builtins.__import__", side_effect=mock_import),
        ):
            # Should not crash on import error
            apps = get_available_apps()

            # Should not include broken app
            assert "broken-app" not in apps

    def test_get_available_apps_skips_non_deploy_modules(self):
        """Test get_available_apps skips modules without deploy function."""
        # This is tested indirectly by the discovery test - modules without deploy
        # functions won't be included in the results
        apps = get_available_apps()

        # All returned apps should have deploy functions
        for app_name, app_info in apps.items():
            assert "deploy_function" in app_info
            assert callable(app_info["deploy_function"])
