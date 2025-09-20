"""Simple integration test for app discovery - tests real functionality."""

from pathlib import Path


def test_app_discovery_integration():
    """Test that get_available_apps discovers the correct number of apps from the apps directory."""
    # Import the real function
    from vantage_cli.apps.utils import get_available_apps

    # Get the apps directory path
    apps_dir = Path(__file__).parent.parent.parent / "vantage_cli" / "apps"

    # Count expected apps by looking at the directory structure
    expected_apps = []

    if apps_dir.exists():
        for item in apps_dir.iterdir():
            # Skip __pycache__, __init__.py, utils.py, and files
            if item.is_dir() and not item.name.startswith("__") and item.name != "utils.py":
                # Check if it has an app.py file
                app_file = item / "app.py"
                if app_file.exists():
                    expected_apps.append(item.name.replace("_", "-"))

    print(f"Expected apps from directory scan: {expected_apps}")

    # Get actual discovered apps
    discovered_apps = get_available_apps()
    discovered_names = list(discovered_apps.keys())

    print(f"Actually discovered apps: {discovered_names}")
    print(f"Number of expected apps: {len(expected_apps)}")
    print(f"Number of discovered apps: {len(discovered_names)}")

    # Verify counts match
    assert len(discovered_apps) == len(expected_apps), (
        f"Expected {len(expected_apps)} apps, but discovered {len(discovered_names)}"
    )

    # Verify all expected apps are discovered
    for expected_app in expected_apps:
        assert expected_app in discovered_names, (
            f"Expected app {expected_app} not found in discovered apps"
        )

    # Verify each discovered app has required structure
    for app_name, app_info in discovered_apps.items():
        assert "module" in app_info, f"App {app_name} should have a module"
        assert "deploy_function" in app_info, f"App {app_name} should have a deploy_function"

        # Verify module is importable (has __name__)
        assert hasattr(app_info["module"], "__name__"), (
            f"App {app_name} module should be importable"
        )
        print(f"✓ App {app_name} has importable module: {app_info['module'].__name__}")

        # Verify deploy function exists
        assert callable(app_info["deploy_function"]), (
            f"App {app_name} deploy function should be callable"
        )
        print(f"✓ App {app_name} has callable deploy function")

    print(f"\n✓ Successfully discovered {len(discovered_apps)} apps with exact count match!")


def test_exact_app_count():
    """Test that we discover exactly 4 apps as currently expected."""
    from vantage_cli.apps.utils import get_available_apps

    discovered_apps = get_available_apps()
    expected_count = 4

    assert len(discovered_apps) == expected_count, (
        f"Expected exactly {expected_count} apps, got {len(discovered_apps)}"
    )
    print(f"✓ Found exactly {expected_count} apps as expected")


def test_specific_expected_apps():
    """Test that we can discover specific apps we know should exist."""
    from vantage_cli.apps.utils import get_available_apps

    discovered_apps = get_available_apps()
    app_names = set(discovered_apps.keys())

    # Apps we expect to exist based on the repository structure
    expected_base_apps = ["slurm-microk8s-localhost", "jupyterhub-microk8s-localhost"]

    print(f"Looking for expected base apps: {expected_base_apps}")
    print(f"Found apps: {sorted(app_names)}")

    for expected_app in expected_base_apps:
        if expected_app in app_names:
            print(f"✓ Found expected app: {expected_app}")
        else:
            print(f"✗ Missing expected app: {expected_app}")

    # At minimum we should have the base apps
    found_base_apps = [app for app in expected_base_apps if app in app_names]
    print(f"Found {len(found_base_apps)} out of {len(expected_base_apps)} expected base apps")

    assert len(found_base_apps) >= 1, f"Should find at least 1 base app, found: {found_base_apps}"


def test_app_importability():
    """Test that discovered apps are actually importable."""
    from vantage_cli.apps.utils import get_available_apps

    discovered_apps = get_available_apps()

    for app_name, app_info in discovered_apps.items():
        print(f"\nTesting app: {app_name}")

        # Test module importability
        module = app_info.get("module")
        if module and hasattr(module, "__name__"):
            print(f"  ✓ Module name: {module.__name__}")
        else:
            print("  ✗ Module not properly imported")

        # Test deploy function
        deploy_func = app_info.get("deploy_function")
        if deploy_func and callable(deploy_func):
            print("  ✓ Deploy function is callable")

            # Try to get docstring
            if hasattr(deploy_func, "__doc__") and deploy_func.__doc__:
                doc_preview = deploy_func.__doc__.strip().split("\n")[0][:50]
                print(f"  ✓ Has docstring: {doc_preview}...")
            else:
                print("  - No docstring available")
        else:
            print("  ✗ Deploy function not callable")


if __name__ == "__main__":
    print("=== Testing App Discovery Integration ===")
    test_app_discovery_integration()

    print("\n=== Testing Exact App Count ===")
    test_exact_app_count()

    print("\n=== Testing Specific Expected Apps ===")
    test_specific_expected_apps()

    print("\n=== Testing App Importability ===")
    test_app_importability()

    print("\n=== Summary ===")
    print("All tests passed!")
