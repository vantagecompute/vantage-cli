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
import sys
import types
from types import SimpleNamespace
from typing import Any, Dict, Optional, Tuple

import pytest
import typer

from vantage_cli.apps.slurm_multipass_localhost import app as multipass_app


class DummyPopen:
    def __init__(self, *args: object, **kwargs: object) -> None:
        self.args: Tuple[object, ...] = args
        self.kwargs: Dict[str, object] = dict(kwargs)
        self.returncode = 0
        self.stdin = types.SimpleNamespace(write=lambda _b: None)  # type: ignore[attr-defined]

    def communicate(self, input: Optional[bytes] = None) -> tuple[str, str]:
        self.input = input  # type: ignore[attr-defined]
        return ("", "")


@pytest.fixture()
def ctx() -> Any:
    # Minimal context object expected by DeploymentContext usage inside deploy()
    settings = SimpleNamespace(
        oidc_domain="auth.example.com",
        oidc_base_url="https://auth.example.com",
        api_base_url="https://api.example.com",
        tunnel_api_url="https://tunnel.example.com",
    )
    return SimpleNamespace(obj=SimpleNamespace(settings=settings))


def _cluster_data(include_secret: bool = True) -> Dict[str, Any]:
    data: Dict[str, Any] = {
        "clientId": "client-123",
        "name": "cluster-1",
        "creationParameters": {"jupyterhub_token": "tok"},
    }
    if include_secret:
        data["clientSecret"] = "sek"
    return data


@pytest.mark.asyncio()
async def test_deploy_missing_binary(monkeypatch: pytest.MonkeyPatch, ctx: Any) -> None:
    monkeypatch.setattr(multipass_app, "which", lambda _name: None)
    with pytest.raises(typer.Exit):
        await multipass_app.deploy(ctx, _cluster_data())


@pytest.mark.asyncio()
async def test_deploy_success(monkeypatch: pytest.MonkeyPatch, ctx: Any) -> None:
    monkeypatch.setattr(multipass_app, "which", lambda _name: "/usr/bin/multipass")

    dummy = DummyPopen()

    def fake_popen(*_a: object, **_k: object) -> DummyPopen:
        return dummy

    monkeypatch.setattr(multipass_app.subprocess, "Popen", fake_popen)
    # Bypass network call for client secret retrieval by returning provided one
    monkeypatch.setattr(multipass_app, "require_client_secret", lambda secret, _c: secret or "sek")
    monkeypatch.setattr(
        multipass_app,
        "validate_cluster_data",
        lambda d, _c: d,
    )
    monkeypatch.setattr(
        multipass_app,
        "validate_client_credentials",
        lambda d, _c: (d["clientId"], d.get("clientSecret")),
    )

    # Avoid importing cluster utils
    async def fake_get_secret(**_kw: object) -> str:
        return "sek"

    monkeypatch.setitem(
        sys.modules,
        "vantage_cli.commands.cluster.utils",
        types.SimpleNamespace(get_cluster_client_secret=fake_get_secret),
    )  # type: ignore[arg-type]
    await multipass_app.deploy(ctx, _cluster_data())
    assert dummy.returncode == 0


@pytest.mark.asyncio()
async def test_deploy_failure_return_code(monkeypatch: pytest.MonkeyPatch, ctx: Any) -> None:
    monkeypatch.setattr(multipass_app, "which", lambda _name: "/usr/bin/multipass")

    dummy = DummyPopen()
    dummy.returncode = 5

    def fake_popen(*_a: object, **_k: object) -> DummyPopen:
        return dummy

    monkeypatch.setattr(multipass_app.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(multipass_app, "require_client_secret", lambda secret, _c: secret or "sek")
    monkeypatch.setattr(
        multipass_app,
        "validate_cluster_data",
        lambda d, _c: d,
    )
    monkeypatch.setattr(
        multipass_app,
        "validate_client_credentials",
        lambda d, _c: (d["clientId"], d.get("clientSecret")),
    )

    async def fake_get_secret(**_kw: object) -> str:
        return "sek"

    monkeypatch.setitem(
        sys.modules,
        "vantage_cli.commands.cluster.utils",
        types.SimpleNamespace(get_cluster_client_secret=fake_get_secret),
    )  # type: ignore[arg-type]
    with pytest.raises(typer.Exit):
        await multipass_app.deploy(ctx, _cluster_data())
