# Cluster Delete App Support

## Overview

Updated the `vantage cluster delete` command to support the `--app` flag, allowing dynamic cleanup of app deployments similar to how `vantage cluster create` works.

## Changes Made

### 1. Dynamic App Discovery

**File**: `vantage_cli/commands/cluster/delete.py`

- **Added import**: `get_available_apps` from `vantage_cli.apps.utils`
- **Removed hard-coded imports**: No longer imports specific app cleanup functions

### 2. New `_call_app_remove_function`

Replaces the old `_call_app_cleanup_function` with a dynamic approach:

```python
async def _call_app_remove_function(
    ctx: typer.Context, app_name: str, deployment: Any
) -> None:
    """Call the appropriate remove function from the app module."""
```

**How it works:**
1. Uses `get_available_apps()` to discover available apps
2. Looks up the app by name (e.g., 'slurm-multipass', 'slurm-lxd')
3. Checks if the app module has a `remove` function
4. Calls the `remove` function with `(ctx, deployment)` parameters

**Benefits:**
- No need to hard-code app names
- Automatically supports new apps that implement a `remove` function
- Consistent with how `cluster create` works

### 3. Updated `_cleanup_single_deployment`

**Before**: Took `deployment: dict[str, Any]`
**After**: Takes `deployment: Any` (Deployment object)

Changes:
- Extracts `deployment_id` from `deployment.id`
- Calls `_call_app_remove_function` instead of hard-coded function
- Better error handling for app-specific errors

### 4. Updated `_cleanup_app_deployments`

**Before**: Used dict iteration and hard-coded app name matching
**After**: Uses list comprehension with Deployment objects

Changes:
- Uses `list_deployments_by_cluster(cluster_name)` without console parameter
- Filters deployments by `deployment.app_name`
- Better console output with status messages
- Returns detailed cleanup results

### 5. Updated Help Text

**Before**: 
```
help="Cleanup the specified app deployment (e.g., slurm-juju-localhost, slurm-multipass-localhost, slurm-microk8s-localhost)"
```

**After**:
```
help="Cleanup the specified app deployment (e.g., slurm-lxd, slurm-multipass, slurm-microk8s)"
```

## Usage

### Basic cluster deletion:
```bash
vantage cluster delete mycluster
```

### Delete cluster and cleanup specific app:
```bash
vantage cluster delete mycluster --app slurm-multipass
```

### With force flag (skip confirmation):
```bash
vantage cluster delete mycluster --app slurm-lxd --force
```

## Expected App Module Structure

For an app to support automatic cleanup with `--app`, it must:

1. Be discoverable by `get_available_apps()`
2. Have a `remove` function with signature:
   ```python
   async def remove(ctx: typer.Context, deployment: Deployment) -> None:
       """Remove the deployment."""
       pass
   ```

## Examples of Compatible Apps

- `slurm-lxd` → `vantage_cli.apps.localhost.slurm_lxd.app.remove()`
- `slurm-multipass` → `vantage_cli.apps.localhost.slurm_multipass.app.remove()`
- `slurm-microk8s` → `vantage_cli.apps.localhost.slurm_microk8s.app.remove()`

## Testing

To test the changes:

```bash
# Create a cluster with an app
vantage cluster create testcluster --cloud localhost --app slurm-multipass

# Delete the cluster and cleanup the app
vantage cluster delete testcluster --app slurm-multipass

# Verify deployments are removed
vantage app deployment list
```

## Error Handling

The implementation gracefully handles:
- App not found in available apps
- App module doesn't have a `remove` function
- Deployment cleanup failures
- Removal from tracking file failures

All errors are logged and reported to the user without crashing the command.
