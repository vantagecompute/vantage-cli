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
from unittest.mock import MagicMock, patch

import pytest

from vantage_cli.commands.cluster.create import create_cluster, deploy_app_to_cluster
from vantage_cli.config import Settings
from vantage_cli.exceptions import Abort


class DummyClient:
    def __init__(self, responses):
        self._responses = list(responses)

    async def execute_async(self, _query, _variables=None):
        return self._responses.pop(0)


class DummyGraphQLFactory:
    def __init__(self, client):
        self._client = client

    def __call__(self, *_a, **_k):
        return self._client


def make_ctx(settings: Settings | None = None):
    # Minimal duck-typed context object matching the attributes accessed by the
    # undecorated create_cluster implementation (ctx.obj.settings / ctx.obj.profile).
    from tests.conftest import MockConsole

    if settings is None:
        settings = Settings()
    return SimpleNamespace(
        obj=SimpleNamespace(settings=settings, profile="test_profile", console=MockConsole())
    )


@pytest.mark.asyncio
async def test_create_cluster_no_response(monkeypatch):
    ctx = make_ctx()
    dummy_client = DummyClient([{}])  # createCluster key missing -> Abort
    monkeypatch.setattr(
        "vantage_cli.commands.cluster.create.create_async_graphql_client",
        DummyGraphQLFactory(dummy_client),
    )
    # Call the original (undecorated) function to avoid decorator file I/O.
    original_fn = create_cluster.__wrapped__  # type: ignore[attr-defined]
    with pytest.raises(Abort) as exc:
        await original_fn(ctx, "c1", cloud=ctx.obj.settings.supported_clouds[0])
    assert "No response" in str(exc.value)


@pytest.mark.asyncio
async def test_create_cluster_error_message(monkeypatch):
    ctx = make_ctx()
    dummy_client = DummyClient([{"createCluster": {"message": "Name taken"}}])
    monkeypatch.setattr(
        "vantage_cli.commands.cluster.create.create_async_graphql_client",
        DummyGraphQLFactory(dummy_client),
    )
    original_fn = create_cluster.__wrapped__  # type: ignore[attr-defined]
    with pytest.raises(Abort) as exc:
        await original_fn(ctx, "c1", cloud=ctx.obj.settings.supported_clouds[0])
    assert "Name taken" in str(exc.value)


@pytest.mark.asyncio
async def test_create_cluster_unclear_status(monkeypatch):
    ctx = make_ctx()
    dummy_client = DummyClient([{"createCluster": {"status": "PENDING"}}])
    monkeypatch.setattr(
        "vantage_cli.commands.cluster.create.create_async_graphql_client",
        DummyGraphQLFactory(dummy_client),
    )
    # Should not raise; prints yellow message path
    original_fn = create_cluster.__wrapped__  # type: ignore[attr-defined]
    await original_fn(ctx, "c1", cloud=ctx.obj.settings.supported_clouds[0])


@pytest.mark.asyncio
async def test_create_cluster_config_file_error(tmp_path, monkeypatch):
    ctx = make_ctx()
    bad_file = tmp_path / "config.json"
    bad_file.write_text("{not valid json}")
    original_fn = create_cluster.__wrapped__  # type: ignore[attr-defined]
    with pytest.raises(Abort) as exc:
        await original_fn(
            ctx,
            "c1",
            cloud=ctx.obj.settings.supported_clouds[0],
            config_file=bad_file,
        )
    assert "Configuration File Error" in str(exc.value.subject)


@pytest.mark.asyncio
async def test_deploy_app_to_cluster_paths(monkeypatch):
    # Prepare ctx and cluster data
    ctx = make_ctx()
    cluster = {"name": "c1"}

    # 1. App not found
    monkeypatch.setattr("vantage_cli.commands.cluster.create.get_available_apps", lambda: {})
    await deploy_app_to_cluster(ctx, cluster, "missing-app")

    # 2. Function based app
    called = {}

    async def deploy_func(_ctx, _cluster):  # pragma: no cover - executed
        called["func"] = True

    monkeypatch.setattr(
        "vantage_cli.commands.cluster.create.get_available_apps",
        lambda: {"func-app": {"deploy_function": deploy_func}},
    )
    await deploy_app_to_cluster(ctx, cluster, "func-app")
    assert called.get("func") is True

    # 3. Class based app with deploy
    class App:
        def __init__(self):
            self.deployed = False

        async def deploy(self, _ctx):  # pragma: no cover - executed
            self.deployed = True

    app_instance = App()
    monkeypatch.setattr(
        "vantage_cli.commands.cluster.create.get_available_apps",
        lambda: {"class-app": {"instance": app_instance}},
    )
    await deploy_app_to_cluster(ctx, cluster, "class-app")
    assert app_instance.deployed is True

    # 4. Class instance without deploy method
    class NoDeploy:
        pass

    monkeypatch.setattr(
        "vantage_cli.commands.cluster.create.get_available_apps",
        lambda: {"nodeploy": {"instance": NoDeploy()}},
    )
    await deploy_app_to_cluster(ctx, cluster, "nodeploy")

    # 5. Unknown spec (neither deploy_function nor instance)
    monkeypatch.setattr(
        "vantage_cli.commands.cluster.create.get_available_apps",
        lambda: {"weird": {"other": 1}},
    )
    await deploy_app_to_cluster(ctx, cluster, "weird")

    # 6. Exception path
    async def boom(*_a, **_k):  # pragma: no cover - executed
        raise RuntimeError("explode")

    monkeypatch.setattr(
        "vantage_cli.commands.cluster.create.get_available_apps",
        lambda: {"boom-app": {"deploy_function": boom}},
    )
    await deploy_app_to_cluster(ctx, cluster, "boom-app")


@pytest.mark.asyncio
async def test_deploy_app_to_cluster_tracks_deployments():
    """Test that deploy_app_to_cluster properly tracks deployments for both function and class-based apps."""
    # Prepare ctx and cluster data
    ctx = MagicMock()
    cluster = {"name": "test-cluster", "clientId": "test-client"}

    # Track calls to track_deployment
    track_deployment_calls = []

    def mock_track_deployment(**kwargs):
        track_deployment_calls.append(kwargs)

    # 1. Test function-based app deployment tracking
    async def deploy_func(_ctx, _cluster):
        pass

    with (
        patch("vantage_cli.commands.cluster.create.get_available_apps") as mock_get_apps,
        patch(
            "vantage_cli.commands.cluster.create.track_deployment",
            side_effect=mock_track_deployment,
        ),
    ):
        mock_get_apps.return_value = {"func-app": {"deploy_function": deploy_func}}
        await deploy_app_to_cluster(ctx, cluster, "func-app")

    # Verify function-based app was tracked
    assert len(track_deployment_calls) == 1
    func_call = track_deployment_calls[0]
    assert func_call["app_name"] == "func-app"
    assert func_call["cluster_name"] == "test-cluster"
    assert func_call["cluster_data"] == cluster
    assert "deployment_id" in func_call
    assert "deployment_name" in func_call
    assert func_call["additional_metadata"]["deployment_method"] == "vantage cluster create --app"
    assert func_call["additional_metadata"]["app_type"] == "function-based"

    # Reset for next test
    track_deployment_calls.clear()

    # 2. Test class-based app deployment tracking
    class TestApp:
        async def deploy(self, _ctx):
            pass

    app_instance = TestApp()

    with (
        patch("vantage_cli.commands.cluster.create.get_available_apps") as mock_get_apps,
        patch(
            "vantage_cli.commands.cluster.create.track_deployment",
            side_effect=mock_track_deployment,
        ),
    ):
        mock_get_apps.return_value = {"class-app": {"instance": app_instance}}
        await deploy_app_to_cluster(ctx, cluster, "class-app")

    # Verify class-based app was tracked
    assert len(track_deployment_calls) == 1
    class_call = track_deployment_calls[0]
    assert class_call["app_name"] == "class-app"
    assert class_call["cluster_name"] == "test-cluster"
    assert class_call["cluster_data"] == cluster
    assert "deployment_id" in class_call
    assert "deployment_name" in class_call
    assert class_call["additional_metadata"]["deployment_method"] == "vantage cluster create --app"
    assert class_call["additional_metadata"]["app_type"] == "class-based"
