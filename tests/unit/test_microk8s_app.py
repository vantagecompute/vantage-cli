#!/usr/bin/env python3
"""Smoke tests for `vantage_cli.apps.slurm_microk8s_localhost.app` to raise coverage safely.

These tests mock out subprocess invocation, filesystem, and external binaries to
exercise branching logic (binary missing, existing values reuse, downloads,
non‑fatal vs fatal command failures) without performing real operations.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Sequence, Tuple
from unittest.mock import MagicMock, patch

import pytest
import typer

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
    mock_ctx.obj = SimpleNamespace(profile="test_profile", settings=SimpleNamespace())
    return mock_ctx


def _patch_run(sequence: Sequence[Tuple[int, str]]) -> Callable[..., DummyCompleted]:
    """Return side effect function simulating subprocess.run returning codes in sequence."""
    calls = {"i": 0}

    def _side_effect(*args: Any, **kwargs: Any) -> DummyCompleted:  # noqa: D401
        i = calls["i"]
        calls["i"] += 1
        code, out = sequence[min(i, len(sequence) - 1)]
        return DummyCompleted(returncode=code, stdout=out)

    return _side_effect


def test_deploy_missing_microk8s_binary(ctx: MagicMock):
    """If microk8s not found deploy should exit with code 1."""
    with patch("vantage_cli.apps.slurm_microk8s_localhost.app.shutil.which", return_value=None):
        with pytest.raises(typer.Exit) as exc:
            ctx2 = MagicMock()
            ctx2.obj = SimpleNamespace(profile="p")
            # call the internal deploy coroutine via run (simpler than invoking deploy_command decorator path)
            import asyncio

            asyncio.run(microk8s_app.deploy(ctx2))
        assert exc.value.exit_code == 1


def test_deploy_happy_path_reuse_existing_values(ctx: MagicMock, tmp_path: Path):
    """Happy path: existing values files cause reuse branch; all commands allow_fail True except first status."""
    # Prepare fake existing values files
    (tmp_path / "microk8s-slurm").mkdir()
    (tmp_path / "microk8s-slurm" / "values-operator.yaml").write_text("op: 1")
    (tmp_path / "microk8s-slurm" / "values-slurm.yaml").write_text("slurm: 1")

    with patch("vantage_cli.apps.slurm_microk8s_localhost.app.Path.cwd", return_value=tmp_path):
        with patch(
            "vantage_cli.apps.slurm_microk8s_localhost.app.shutil.which",
            side_effect=["/usr/bin/microk8s", "/usr/bin/helm"],
        ):
            # Fake run result
            run_seq = [(0, "ok") for _ in range(20)]
            with patch(
                "vantage_cli.apps.slurm_microk8s_localhost.app.subprocess.run",
                side_effect=_patch_run(run_seq),
            ):
                import asyncio

                asyncio.run(microk8s_app.deploy(ctx))  # Should not raise


def test_deploy_download_values_when_missing(ctx: MagicMock, tmp_path: Path):
    """When values files missing, curl commands (allow_fail False) must run; simulate success."""
    (tmp_path / "microk8s-slurm").mkdir()
    # Only create one file so other triggers download
    (tmp_path / "microk8s-slurm" / "values-operator.yaml").write_text("op: 1")

    with patch("vantage_cli.apps.slurm_microk8s_localhost.app.Path.cwd", return_value=tmp_path):
        with patch(
            "vantage_cli.apps.slurm_microk8s_localhost.app.shutil.which",
            side_effect=["/usr/bin/microk8s", "/usr/bin/helm"],
        ):
            # Provide enough successful runs
            run_seq = [(0, "ok") for _ in range(20)]
            with patch(
                "vantage_cli.apps.slurm_microk8s_localhost.app.subprocess.run",
                side_effect=_patch_run(run_seq),
            ):
                import asyncio

                asyncio.run(microk8s_app.deploy(ctx))


def test_deploy_fatal_command_failure(ctx: MagicMock, tmp_path: Path):
    """A fatal command (status) with non-zero and not allow_fail should raise Exit with its code."""
    (tmp_path / "microk8s-slurm").mkdir(exist_ok=True)
    (tmp_path / "microk8s-slurm" / "values-operator.yaml").write_text("op: 1")
    (tmp_path / "microk8s-slurm" / "values-slurm.yaml").write_text("slurm: 1")

    with patch("vantage_cli.apps.slurm_microk8s_localhost.app.Path.cwd", return_value=tmp_path):
        with patch(
            "vantage_cli.apps.slurm_microk8s_localhost.app.shutil.which",
            side_effect=["/usr/bin/microk8s", "/usr/bin/helm"],
        ):
            # First run (status) fails (code 2) -> should raise
            run_seq = [(2, "boom"), (0, "ignored")]  # subsequent not used
            with patch(
                "vantage_cli.apps.slurm_microk8s_localhost.app.subprocess.run",
                side_effect=_patch_run(run_seq),
            ):
                import asyncio

                with pytest.raises(typer.Exit) as exc:
                    asyncio.run(microk8s_app.deploy(ctx))
                assert exc.value.exit_code == 2


def test_deploy_nonfatal_command_failure(ctx: MagicMock, tmp_path: Path):
    """A non-fatal addon enable command (allow_fail True) returns non-zero but continues."""
    (tmp_path / "microk8s-slurm").mkdir(exist_ok=True)
    (tmp_path / "microk8s-slurm" / "values-operator.yaml").write_text("op: 1")
    (tmp_path / "microk8s-slurm" / "values-slurm.yaml").write_text("slurm: 1")

    with patch("vantage_cli.apps.slurm_microk8s_localhost.app.Path.cwd", return_value=tmp_path):
        with patch(
            "vantage_cli.apps.slurm_microk8s_localhost.app.shutil.which",
            side_effect=["/usr/bin/microk8s", "/usr/bin/helm"],
        ):
            # status ok, then first addon enable fails but allow_fail=True so continues
            run_seq = [(0, "ready"), (1, "already enabled"), (0, "rest ok"), (0, "rest ok")] * 5
            with patch(
                "vantage_cli.apps.slurm_microk8s_localhost.app.subprocess.run",
                side_effect=_patch_run(run_seq),
            ):
                import asyncio

                asyncio.run(microk8s_app.deploy(ctx))  # Should not raise
