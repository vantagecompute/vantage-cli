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
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest
import typer
from juju.errors import JujuError

from vantage_cli.apps.slurm_juju_localhost import app as juju_app


@pytest.fixture()
def ctx() -> Any:
    return SimpleNamespace()


def _cluster_data(include_secret: bool = True, include_token: bool = True) -> Dict[str, Any]:
    data: Dict[str, Any] = {"clientId": "client-123"}
    if include_secret:
        data["clientSecret"] = "sek"
    if include_token:
        data["creationParameters"] = {"jupyterhub_token": "tok"}
    return data


# --------------------------------- Existing high-level deploy() tests ---------------------------------


@pytest.mark.asyncio()
async def test_deploy_missing_token(monkeypatch: pytest.MonkeyPatch, ctx: Any) -> None:
    # Provide clientId & secret but no jupyterhub token
    with pytest.raises(typer.Exit):
        await juju_app.deploy(ctx, _cluster_data(include_token=False))


@pytest.mark.asyncio()
async def test_deploy_with_secret(monkeypatch: pytest.MonkeyPatch, ctx: Any) -> None:
    # Patch out heavy deploy
    async def fake_inner(_c: object) -> None:
        return None

    monkeypatch.setattr(juju_app, "deploy_juju_localhost", fake_inner)
    await juju_app.deploy(ctx, _cluster_data())


@pytest.mark.asyncio()
async def test_deploy_secret_via_env(monkeypatch: pytest.MonkeyPatch, ctx: Any) -> None:
    # Missing secret in data, provide via env var
    async def fake_inner(_c: object) -> None:
        return None

    monkeypatch.setattr(juju_app, "deploy_juju_localhost", fake_inner)
    monkeypatch.setenv("VANTAGE_CLIENT_SECRET", "sek")
    await juju_app.deploy(ctx, _cluster_data(include_secret=False))


# --------------------------------- Helper function tests ---------------------------------


def test_build_secret_args() -> None:
    class Dummy:
        client_id = "cid"
        client_secret = "csec"
        oidc_base_url = "http://oidc"  # type: ignore
        tunnel_api_url = "http://tunnel"  # type: ignore
        base_api_url = "http://api"  # type: ignore
        oidc_domain = "dom"  # type: ignore
        jupyterhub_token = "tok"  # type: ignore

    args = juju_app._build_secret_args(Dummy())
    assert args == [
        "oidc-client-id=cid",
        "oidc-client-secret=csec",
        "oidc-base-url=http://oidc",
        "tunnel-api-url=http://tunnel",
        "vantage-api-url=http://api",
        "oidc-domain=dom",
        "jupyterhub-token=tok",
    ]


def test_prepare_bundle() -> None:
    class Dummy:
        client_id = "cid"
        client_secret = "csec"
        base_api_url = "http://api"
        oidc_domain = "dom"

    bundle = juju_app._prepare_bundle(Dummy(), "modelx", "secret-1")
    assert bundle["applications"]["slurmctld"]["options"]["cluster-name"] == "modelx"
    assert (
        bundle["applications"]["vantage-agent"]["options"]["vantage-agent-oidc-client-secret"]
        == "csec"
    )
    assert (
        bundle["applications"]["vantage-jupyterhub"]["options"][
            "vantage-jupyterhub-config-secret-id"
        ]
        == "secret-1"
    )


# --------------------------------- Fakes for deploy_juju_localhost tests ---------------------------------


class FakeAction:
    def __init__(self, results: Dict[str, Any]):
        self.results = results

    async def wait(self) -> None:  # pragma: no cover - trivial
        return None


class FakeUnit:
    def __init__(self, name: str, leader: bool = False, influx_conf: str | None = None):
        self.name = name
        self._leader = leader
        self._influx_conf = influx_conf
        self.run_actions: List[str] = []

    async def run_action(self, name: str) -> FakeAction:
        self.run_actions.append(name)
        return FakeAction({"return-code": 0, "stdout": "", "stderr": ""})

    async def is_leader_from_status(self) -> bool:  # pragma: no cover - simple
        return self._leader

    async def run(self, _cmd: str) -> FakeAction:
        # Return fake influx config if provided
        conf = (
            self._influx_conf
            or "profileinfluxdbhost=host\nprofileinfluxdbuser=user\nprofileinfluxdbpass=pw\nprofileinfluxdbdatabase=db\nprofileinfluxdbrtpolicy=rp\n"
        )
        return FakeAction({"return-code": 0, "stdout": conf, "stderr": ""})


class FakeApplication:
    def __init__(self, units: List[FakeUnit]):
        self.units = units
        self.config_set: Dict[str, Any] | None = None

    async def set_config(self, cfg: Dict[str, Any]) -> None:
        self.config_set = cfg


class FakeModel:
    def __init__(self, with_slurmd: bool = True, influx_complete: bool = True):
        self.granted: List[str] = []
        self.deployed_bundle_path: str | None = None
        self.secret_args: List[str] | None = None
        self.wait_called = False
        self._raise_wait = False
        slurmd_units = [FakeUnit("slurmd/0")]
        self.applications: Dict[str, Any] = {}
        if with_slurmd:
            self.applications["slurmd"] = FakeApplication(slurmd_units)
        # slurmctld with leader
        influx_conf = None
        if influx_complete:
            influx_conf = (
                "profileinfluxdbhost=host\nprofileinfluxdbuser=user\nprofileinfluxdbpass=pw\n"
                "profileinfluxdbdatabase=db\nprofileinfluxdbrtpolicy=rp\n"
            )
        else:
            influx_conf = (
                "profileinfluxdbhost=host\nprofileinfluxdbuser=user\nprofileinfluxdbdatabase=db\n"
            )
        self.applications["slurmctld"] = FakeApplication(
            [FakeUnit("slurmctld/0", leader=True, influx_conf=influx_conf)]
        )
        self.applications["jobbergate-agent"] = FakeApplication([])

    async def add_secret(self, name: str, args: List[str]):  # pragma: no cover - trivial
        self.secret_args = args
        return "secret-id-123"

    async def deploy(self, path: str) -> None:
        self.deployed_bundle_path = path

    async def grant_secret(
        self, _secret_name: str, _app: str
    ) -> None:  # pragma: no cover - trivial
        self.granted.append(_secret_name)

    async def wait_for_idle(self) -> None:
        self.wait_called = True
        if self._raise_wait:
            raise JujuError("boom")

    async def disconnect(self) -> None:  # pragma: no cover - trivial
        return None


class FakeController:
    def __init__(self, model: FakeModel):
        self._model = model
        self.connected = False
        self.disconnected = False
        self.controller_name = "test-controller"

    async def connect(self) -> None:  # pragma: no cover - trivial
        self.connected = True

    async def add_model(self, _name: str, cloud_name: str):  # pragma: no cover - simple
        return self._model

    async def disconnect(self) -> None:  # pragma: no cover - trivial
        self.disconnected = True


@pytest.mark.asyncio()
async def test_deploy_juju_success_path(monkeypatch: pytest.MonkeyPatch) -> None:
    model = FakeModel()
    controller = FakeController(model)

    # Patch Controller used inside module
    monkeypatch.setattr(juju_app, "Controller", lambda: controller)

    # Patch bundle writer to avoid filesystem gymnastics but still capture bundle
    written_bundle: Dict[str, Any] | None = None

    async def fake_write(model_obj, bundle_yaml):  # type: ignore
        nonlocal written_bundle
        written_bundle = bundle_yaml
        # Simulate deploy side-effect
        await model_obj.deploy("./bundle.yaml")

    monkeypatch.setattr(juju_app, "_write_and_deploy_model_bundle", fake_write)

    class Ctx:
        client_id = "client-123-aaaa-bbbb-cccc"  # ensures model name trimming works
        client_secret = "sek"
        base_api_url = "http://api"
        oidc_base_url = "http://oidc"
        oidc_domain = "dom"
        tunnel_api_url = "http://tunnel"
        jupyterhub_token = "tok"

    result = await juju_app.deploy_juju_localhost(Ctx())
    assert result is None
    assert model.deployed_bundle_path == "./bundle.yaml"
    assert model.wait_called is True
    assert (
        "secret-id-123"
        in written_bundle["applications"]["vantage-jupyterhub"]["options"][
            "vantage-jupyterhub-config-secret-id"
        ]
    )  # type: ignore


@pytest.mark.asyncio()
async def test_deploy_juju_wait_for_idle_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    model = FakeModel()
    model._raise_wait = True  # type: ignore
    controller = FakeController(model)
    monkeypatch.setattr(juju_app, "Controller", lambda: controller)

    async def fake_write(model_obj, bundle_yaml):  # type: ignore
        await model_obj.deploy("./bundle.yaml")

    monkeypatch.setattr(juju_app, "_write_and_deploy_model_bundle", fake_write)

    class Ctx:
        client_id = "client-123-aaaa-bbbb-cccc"
        client_secret = "sek"
        base_api_url = "http://api"
        oidc_base_url = "http://oidc"
        oidc_domain = "dom"
        tunnel_api_url = "http://tunnel"
        jupyterhub_token = "tok"

    exit_obj = await juju_app.deploy_juju_localhost(Ctx())
    assert isinstance(exit_obj, typer.Exit)
    assert exit_obj.exit_code == 1


@pytest.mark.asyncio()
async def test_run_slurmd_node_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    model = FakeModel()
    # Use real helper
    await juju_app._run_slurmd_node_configured(model)
    # Ensure action executed
    slurmd_app = model.applications["slurmd"]
    assert slurmd_app.units[0].run_actions == ["node-configured"]


@pytest.mark.asyncio()
async def test_configure_jobbergate_influxdb_success(monkeypatch: pytest.MonkeyPatch) -> None:
    model = FakeModel(influx_complete=True)
    await juju_app._configure_jobbergate_influxdb(model)
    jb_app = model.applications["jobbergate-agent"]
    assert jb_app.config_set == {"jobbergate-agent-influx-dsn": "influxdb://user:pw@host/db?rp=rp"}


@pytest.mark.asyncio()
async def test_configure_jobbergate_influxdb_incomplete(monkeypatch: pytest.MonkeyPatch) -> None:
    model = FakeModel(influx_complete=False)
    await juju_app._configure_jobbergate_influxdb(model)
    jb_app = model.applications["jobbergate-agent"]
    # Should not have set configuration due to incomplete params
    assert jb_app.config_set is None


@pytest.mark.asyncio()
async def test_write_and_deploy_model_bundle(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Use a lightweight fake model capturing deploy path
    class Model:
        def __init__(self):
            self.deployed = None

        async def deploy(self, path: str):  # pragma: no cover - trivial
            self.deployed = path

    model = Model()
    bundle = {"a": 1}
    await juju_app._write_and_deploy_model_bundle(model, bundle)
    assert model.deployed == "./bundle.yaml"
