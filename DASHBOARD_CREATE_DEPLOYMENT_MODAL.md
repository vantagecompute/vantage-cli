# Dashboard Create Deployment Modal

## Overview
Added a modal dialog for creating deployments from the main dashboard, triggered by the "Create" button.

## Changes Made

### 1. New Imports

Added to `/home/bdx/allcode/github/vantagecompute/vantage-cli/vantage_cli/dashboard/__init__.py`:

```python
from textual.screen import ModalScreen
from textual.widgets import Input, Label, Select
from vantage_cli.sdk.cluster import cluster_sdk
```

### 2. New Class: `DeploymentCreateModal`

A modal screen that allows users to create deployments interactively.

**Features:**
- App selection dropdown (Select widget)
- Cluster selection dropdown (Select widget) 
- Create button (confirms and creates)
- Cancel button (closes modal)

**Layout:**
```
┌─────────────────────────────────────┐
│ 🚀 Create New Deployment            │
│                                     │
│  App:      [Select application...] │
│  Cluster:  [Select cluster...]     │
│                                     │
│      [Create]    [Cancel]           │
└─────────────────────────────────────┘
```

**Styling:**
- 80 characters wide
- Auto height
- Centered on screen
- Form layout with labels and inputs
- Success/Error button variants

**Methods:**
- `compose()` - Creates the modal layout
- `on_button_pressed()` - Handles Create/Cancel button clicks
- `_create_deployment()` - Validates and returns selected values

### 3. Updated `action_start_execution()`

The "Create" button now triggers deployment creation instead of worker execution.

**Before:**
```python
def action_start_execution(self):
    """Start worker execution"""
    self.execution_running = True
    self.run_worker(self.execute_workers, exclusive=True)
```

**After:**
```python
def action_start_execution(self):
    """Open the deployment creation modal."""
    if not self.ctx:
        self.add_log("❌ No context available", "ERROR")
        return
    
    self.run_worker(self._show_create_deployment_modal(), exclusive=True)
```

### 4. New Method: `_show_create_deployment_modal()`

Async worker that:
1. Loads available clusters from SDK
2. Gets list of available apps
3. Shows the modal
4. Handles the result

```python
async def _show_create_deployment_modal(self) -> None:
    # Load clusters
    clusters = await cluster_sdk.list_clusters(self.ctx)
    
    # Get available apps (currently hardcoded, can be dynamic)
    apps = ["slurm-lxd", "slurm-multipass", "jupyterhub"]
    
    # Show modal and wait for result
    result = await self.push_screen_wait(
        DeploymentCreateModal(self.ctx, clusters, apps)
    )
    
    if result:
        await self._create_deployment_from_modal(result)
```

### 5. New Method: `_create_deployment_from_modal()`

Handles deployment creation from modal data:

```python
async def _create_deployment_from_modal(self, data: Dict[str, Any]) -> None:
    app_name = data["app"]
    cluster = data["cluster"]
    
    # Log the creation
    self.add_log(f"🚀 Creating deployment: {app_name} on {cluster.name}...", "INFO")
    
    # TODO: Call the app's create() function
    # For now, just shows success and reloads deployments
    
    self.load_deployments()
```

## User Experience

### Workflow

1. **Click "Create" button** on the right side of the dashboard
2. **Modal appears** with app and cluster dropdowns
3. **Select an application** from the dropdown (e.g., "slurm-lxd")
4. **Select a cluster** from the dropdown (e.g., "my-cluster")
5. **Click "Create"** to initiate deployment creation
   - Modal closes
   - Success message appears in activity log
   - Deployments table refreshes automatically
6. **Or click "Cancel"** to close without creating

### Validation

- Modal checks that both app and cluster are selected
- If not selected, modal stays open
- If cluster not found, logs error and closes

### Future Enhancements (TODO)

Currently, the actual deployment creation just logs success. To complete:

1. **Load apps dynamically** from `vantage_cli.apps.utils`
2. **Call app's create() function** with cluster parameter
3. **Add progress indicator** during creation
4. **Handle errors** and show specific error messages
5. **Add more fields** (substrate selection, configuration options)

## Integration Points

### With Cluster SDK
- Uses `cluster_sdk.list_clusters()` to populate cluster dropdown
- Passes selected Cluster object to deployment creation

### With Deployment SDK  
- After creation, calls `self.load_deployments()` to refresh the table
- Will use deployment_sdk to actually create the deployment (TODO)

### With App System
- Currently hardcoded app list: `["slurm-lxd", "slurm-multipass", "jupyterhub"]`
- Should be replaced with dynamic app discovery

## Files Modified

1. `/home/bdx/allcode/github/vantagecompute/vantage-cli/vantage_cli/dashboard/__init__.py`
   - Added `DeploymentCreateModal` class (146 lines)
   - Updated `action_start_execution()` to show modal
   - Added `_show_create_deployment_modal()` async worker
   - Added `_create_deployment_from_modal()` handler
   - Added imports: ModalScreen, Input, Label, Select, cluster_sdk

## Testing

Run the dashboard:
```bash
uv run vantage cli-dash
```

1. Click the **"Create"** button on the right side
2. Modal should appear with app and cluster dropdowns
3. Select an app and cluster
4. Click **"Create"**
5. Modal should close
6. Success message should appear
7. Deployments table should update (after actual creation is implemented)

## Benefits

1. **User-Friendly**: No need to use CLI commands to create deployments
2. **Interactive**: Dropdowns show available options
3. **Integrated**: Works seamlessly with the dashboard
4. **Reusable**: Modal pattern can be used for other operations
5. **Type-Safe**: Uses SDK schemas for clusters

## Next Steps

To complete the deployment creation:

1. Implement actual app create() calling logic
2. Add dynamic app discovery from apps directory
3. Add substrate selection for multi-substrate apps
4. Add configuration options specific to each app
5. Add progress/loading indicators
6. Add better error handling and user feedback
