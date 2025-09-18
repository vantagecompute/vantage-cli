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
"""Smoke tests for `vantage_cli.apps.slurm_microk8s_localhost.app` to raise coverage safely.

These tests mock out subprocess invocation, filesystem, and external binaries to
exercise branching logic (binary missing, existing values reuse, downloads,
non‑fatal vs fatal command failures) without performing real operations.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import typer

from tests.conftest import MockConsole
from vantage_cli.apps.slurm_microk8s_localhost import app as microk8s_app


class DummyCompleted:
    def __init__(self, returncode: int = 0, stdout: str = "ok") -> None:
        self.returncode: int = returncode
        self.stdout: str = stdout


@pytest.fixture
def ctx() -> MagicMock:
    """Provide a minimal Typer context object with obj.profile & settings for decorator."""
    # The deploy() function itself doesn't need settings; deploy_command attaches them.
    mock_ctx = MagicMock()
    mock_settings = SimpleNamespace()
    mock_settings.oidc_domain = "auth.example.com"
    mock_ctx.obj = SimpleNamespace(
        profile="test_profile", settings=mock_settings, console=MockConsole()
    )
    return mock_ctx


def test_deploy_missing_microk8s_binary(ctx: MagicMock):
    """If microk8s not found deploy should exit with code 1."""
    cluster_data = {
        "name": "test-cluster",
        "clientId": "test-client",
        "clientSecret": "test-secret",
        "creationParameters": {"cloud": "localhost"},
    }

    with patch("vantage_cli.apps.slurm_microk8s_localhost.app.shutil.which", return_value=None):
        with pytest.raises(typer.Exit) as exc:
            ctx2 = MagicMock()
            ctx2.obj = SimpleNamespace(profile="p", console=MockConsole())
            # call the internal deploy coroutine via run (simpler than invoking deploy_command decorator path)
            import asyncio

            asyncio.run(microk8s_app.deploy(ctx2, cluster_data=cluster_data))
        assert exc.value.exit_code == 1


def test_deploy_happy_path_reuse_existing_values(ctx: MagicMock, tmp_path: Path):
    """Happy path: existing values files cause reuse branch; all commands allow_fail True except first status."""
    cluster_data = {
        "name": "test-cluster",
        "clientId": "test-client",
        "clientSecret": "test-secret",
        "creationParameters": {"cloud": "localhost"},
    }

    # Prepare fake existing values files
    (tmp_path / "microk8s-slurm").mkdir()
    (tmp_path / "microk8s-slurm" / "values-operator.yaml").write_text("op: 1")
    (tmp_path / "microk8s-slurm" / "values-slurm.yaml").write_text("slurm: 1")

    with patch("vantage_cli.apps.slurm_microk8s_localhost.app.Path.cwd", return_value=tmp_path):
        with patch(
            "vantage_cli.apps.slurm_microk8s_localhost.app.shutil.which",
            side_effect=["/usr/bin/microk8s", "/usr/bin/helm"],
        ):
            with patch("vantage_cli.apps.slurm_microk8s_localhost.app._run") as mock_run:
                with patch("pathlib.Path.exists") as mock_path_exists:
                    with patch("pathlib.Path.write_text"):
                        with patch("pathlib.Path.chmod"):
                            with patch("pathlib.Path.read_text") as mock_read_text:
                                # Mock SSH key files using direct return values
                                mock_path_exists.return_value = True
                                mock_read_text.return_value = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDCXoCSZMeQTYccOrpmKk/PEVsv+9G4jECi8phLa8r6WZeh/glq7FikIhsSH1I7B5Lef2GXjc59fPr4fpl1Yi4faEmAE+bqQia0gciczClNXYuZzFUH7ynRIw5eauE44MKjy3c/Sy0hXO8DU6WuF72AahooUilVYia0r6ihnth7GJ6ngw1LYnI4zyRIc6mLY7dPGF71LcJfLaddBtuYOFDsMEICqA1M25ax3+Cdshl76DTwxypdGW9Ja/vNIioLQ2gcjjIInXSDYdGi8xCiM1/Iyzl4G/ZpV/pv7dgiryT73DxN5stma+kPUyx9AUub+NU1AOXoE+P2ehi9x1XNIH2dLl+d3y/6GNmuPNdZuOdbkNo3NV1cwTgJ1oaA2b06bBAWJOpm/qVgeZ8Z0ifBUyYdkvqNioVjaL1FpLiapA7MeAsgmCfPgDkMSvijCcgDWXkBBIn3jfUbVbOu1O/jUSc9naockPzxi63z43+YJ7u9PkbVEyhCCHW+q4Djj0xBkcE= bdx@ultra"

                                # Mock _run to return successful completions
                                mock_run.return_value = DummyCompleted(
                                    returncode=0, stdout="success"
                                )

                                import asyncio

                                asyncio.run(
                                    microk8s_app.deploy(ctx, cluster_data=cluster_data)
                                )  # Should not raise
                                # Verify mocked function was called (indicating deployment was mocked)
                                assert mock_run.called
