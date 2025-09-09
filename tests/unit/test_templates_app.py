import pytest

from vantage_cli.apps.templates import CloudInitTemplate, DeploymentContext
from vantage_cli.exceptions import ConfigurationError


def make_context() -> DeploymentContext:
    return DeploymentContext(
        cluster_name="c1",
        client_id="client-123",
        client_secret="secret",
        base_api_url="https://api.example.com",
        oidc_domain="auth.example.com",
        oidc_base_url="https://auth.example.com",
        tunnel_api_url="https://tunnel.example.com",
        jupyterhub_token="token123",
    )


def test_generate_multipass_config_happy_path() -> None:
    tpl = CloudInitTemplate()
    ctx = make_context()
    out = tpl.generate_multipass_config(ctx)
    assert out.startswith("#cloud-config")
    # Ensure a few key substitutions / commands are present (positive assertions)
    assert "snap set vantage-agent base-api-url" in out
    # JupyterHub token should appear in generated commands
    assert "JUPYTERHUB_TOKEN=token123" in out


def test_generate_multipass_config_error(monkeypatch: pytest.MonkeyPatch) -> None:
    tpl = CloudInitTemplate()

    # Force internal builder to raise a TypeError which we wrap as ConfigurationError
    def boom(*_a: object, **_kw: object) -> None:
        raise TypeError("explode")

    monkeypatch.setattr(tpl, "_build_runcmd_list", boom)
    with pytest.raises(ConfigurationError):
        tpl.generate_multipass_config(make_context())
