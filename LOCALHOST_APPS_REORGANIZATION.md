# Localhost Apps Reorganization

## Overview

Reorganized the localhost deployment applications by:
1. Moving them from `vantage_cli/apps/` to `vantage_cli/apps/localhost/`
2. Removing the `_localhost` postfix from module directory names

## Changes Made

### Directory Structure

**Before:**
```
vantage_cli/apps/
├── slurm_lxd_localhost/
├── slurm_multipass_localhost/
└── slurm_microk8s_localhost/
```

**After:**
```
vantage_cli/apps/
└── localhost/
    ├── __init__.py
    ├── slurm_lxd/
    ├── slurm_multipass/
    └── slurm_microk8s/
```

### Module Name Changes

| Old Module Path | New Module Path |
|----------------|-----------------|
| `vantage_cli.apps.slurm_lxd_localhost.app` | `vantage_cli.apps.localhost.slurm_lxd.app` |
| `vantage_cli.apps.slurm_multipass_localhost.app` | `vantage_cli.apps.localhost.slurm_multipass.app` |
| `vantage_cli.apps.slurm_microk8s_localhost.app` | `vantage_cli.apps.localhost.slurm_microk8s.app` |

### Files Modified

#### 1. Core App Files

**`vantage_cli/apps/localhost/__init__.py`** - Created
- Added package documentation describing the three localhost apps

**`vantage_cli/apps/localhost/slurm_multipass/app.py`**
- Added missing import: `from vantage_cli.sdk.deployment.schema import Deployment`

**`vantage_cli/apps/localhost/slurm_microk8s/app.py`**
- Fixed imports: Moved `PrerequisiteStatus` and `check_prerequisites` from local utils to `vantage_cli.apps.utils`

#### 2. Utility Files

**`vantage_cli/apps/utils.py`**
- Updated comments to reflect new structure (e.g., `localhost/slurm_lxd` instead of `localhost/slurm_lxd_localhost`)

**`vantage_cli/commands/cluster/delete.py`**
- No changes needed (already uses dynamic app discovery)

#### 3. Test Files

**`tests/unit/test_app_list_isolated.py`**
- Updated mock module paths from `slurm_microk8s_localhost` to `slurm_microk8s`

**`tests/unit/test_app_list.py`**
- Updated mock module paths from `slurm_microk8s_localhost` to `slurm_microk8s`

**`tests/unit/test_app_list_simple.py`**
- Updated mock module paths in two locations from `slurm_microk8s_localhost` to `slurm_microk8s`

### App Discovery

The app discovery system in `vantage_cli/apps/utils.py` automatically handles the nested structure:

```python
# Nested app detection
if parent_dir.name != "apps" and apps_dir.name == "apps":
    # Nested app (e.g., localhost/slurm_lxd)
    category = parent_dir.name
    app_module = importlib.import_module(f"vantage_cli.apps.{category}.{app_name}.app")
```

This allows apps to be organized in category subdirectories (like `localhost/`) while maintaining backward compatibility with top-level apps.

### Benefits

1. **Better Organization**: Localhost apps are grouped together under a common category
2. **Cleaner Names**: Removed redundant `_localhost` suffix from module names
3. **Scalability**: Can add more categories (e.g., `aws/`, `azure/`, `gcp/`) in the future
4. **Shorter Paths**: Module paths are more concise without the suffix

### Testing

All apps tested and verified:

```bash
$ uv run vantage apps
```

Results:
- ✅ `slurm-lxd` - Module: `vantage_cli.apps.localhost.slurm_lxd.app`
- ✅ `slurm-microk8s` - Module: `vantage_cli.apps.localhost.slurm_microk8s.app`
- ✅ `slurm-multipass` - Module: `vantage_cli.apps.localhost.slurm_multipass.app`

### Migration Notes

- Old backup directories remain in `bak/` with old naming
- No user-facing command changes - app names stay the same (kebab-case)
- All functionality preserved, only internal organization changed
