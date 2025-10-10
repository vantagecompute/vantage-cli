"""Regression tests ensuring the SLURM MicroK8s app is discoverable."""

from vantage_cli.apps.utils import get_available_apps


def test_slurm_microk8s_app_is_registered():
    """The app discovery registry should include the slurm-microk8s app."""
    apps = get_available_apps()

    assert "slurm-microk8s" in apps, "slurm-microk8s should be listed among available apps"

    app_info = apps["slurm-microk8s"]

    module = app_info.get("module")
    assert module is not None and hasattr(module, "__name__"), "App module must be importable"

    create_func = app_info.get("create_function")
    assert callable(create_func), "App entry must expose a callable create_function"
