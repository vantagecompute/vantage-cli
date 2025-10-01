# Command Refactoring Summary

## Overview
Refactored profile, cluster, and notebook commands to follow a consistent architectural pattern:
- **SDK Layer**: Pure business logic, returns Python objects
- **Commands Layer**: CLI interface using SDK + UniversalOutputFormatter
- **Presentation Layer**: All formatting handled by UniversalOutputFormatter

## Changes Made

### 1. Profile Commands (Previously Completed)
All profile commands (list, get, create, update, delete, activate) now use:
- `ProfileSDK` for business logic
- `UniversalOutputFormatter` for consistent output
- Proper separation of concerns

### 2. Cluster Commands

#### Cluster List Command (`vantage_cli/commands/cluster/list.py`)
**Before:**
- Used `RenderStepOutput` with progress steps
- Called `render_clusters_table()` for table rendering
- Mixed business and presentation logic

**After:**
- Uses `cluster_sdk.list_clusters()` to get Cluster objects
- Converts Cluster objects to dictionaries
- Uses `UniversalOutputFormatter.render_list()` for consistent output
- Handles both table and JSON output automatically

#### Cluster Get Command (`vantage_cli/commands/cluster/get.py`)
**Before:**
- Used `get_cluster_by_name()` utility function
- Used `RenderStepOutput` with table steps
- Called `render_cluster_details()` for rendering

**After:**
- Uses `cluster_sdk.get_cluster()` to get Cluster object
- Converts Cluster object to dictionary
- Uses `UniversalOutputFormatter.render_get()` for consistent output
- Proper error handling with formatter

#### Cluster SDK (`vantage_cli/sdk/cluster/crud.py`)
**Status:** Already clean!
- Contains only business logic
- Returns Cluster objects (not dicts)
- Methods: `list_clusters()`, `get_cluster()`
- No rendering code present

### 3. Notebook Commands

#### Notebook SDK (`vantage_cli/sdk/notebook/crud.py`)
**Created new SDK:**
- `NotebookSDK` class with GraphQL-based operations
- Methods: `list_notebooks()`, `get_notebook()`
- Returns strongly-typed `Notebook` objects
- Handles GraphQL query execution and error handling
- Client-side filtering for cluster parameter

#### Notebook Schema (`vantage_cli/schemas.py`)
**Added new schema:**
```python
class Notebook(BaseModel):
    id: str
    name: str
    cluster_name: Optional[str] = None
    partition: Optional[str] = None
    owner: Optional[str] = None
    server_url: Optional[str] = None
    slurm_job_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
```

#### Notebook List Command (`vantage_cli/commands/notebook/list.py`)
**Before:**
- Direct GraphQL queries in command
- Used `RenderStepOutput` with progress steps
- Called `render_notebooks_table()` for rendering

**After:**
- Uses `notebook_sdk.list_notebooks()` to get Notebook objects
- Converts Notebook objects to dictionaries
- Uses `UniversalOutputFormatter.render_list()` for consistent output
- Cleaner error handling and no GraphQL in command layer

#### Notebook Get Command (`vantage_cli/commands/notebook/get.py`)
**Before:**
- Direct GraphQL queries in command
- Used `RenderStepOutput` with panel steps
- Called `render_notebook_details()` for rendering

**After:**
- Uses `notebook_sdk.get_notebook()` to get Notebook object
- Converts Notebook object to dictionary
- Uses `UniversalOutputFormatter.render_get()` for consistent output
- Proper error handling with formatter

### 4. Job Commands
**Status:** Already refactored! ✅
- All job script, submission, and template commands already use `UniversalOutputFormatter`
- No `RenderStepOutput` usage found
- Commands follow the same pattern as profile/cluster/notebook commands
- Job commands use REST API client instead of GraphQL

### 5. Support Ticket Commands

#### Support Ticket SDK (`vantage_cli/sdk/support_ticket/crud.py`)
**Created new SDK:**
- `SupportTicketSDK` class with full CRUD operations
- Methods: `list_tickets()`, `get_ticket()`, `create_ticket()`, `update_ticket()`, `delete_ticket()`
- Returns strongly-typed `SupportTicket` objects
- Handles GraphQL mutations and queries
- Graceful fallback if API endpoint not available yet

#### Support Ticket Schema (`vantage_cli/schemas.py`)
**Added new schema:**
```python
class SupportTicket(BaseModel):
    id: str
    subject: str
    description: str
    status: str
    priority: str
    owner_email: str
    assigned_to: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None
    resolved_at: Optional[str] = None
```

#### Support Ticket List Command (`vantage_cli/commands/support_ticket/list.py`)
**Before:**
- Mock implementation with print_json
- No real API integration

**After:**
- Uses `support_ticket_sdk.list_tickets()` to get SupportTicket objects
- Supports `--status`, `--priority`, `--limit` filters
- Converts SupportTicket objects to dictionaries
- Uses `UniversalOutputFormatter.render_list()` for consistent output
- Proper error handling with formatter

#### Support Ticket Get Command (`vantage_cli/commands/support_ticket/get.py`)
**Before:**
- Mock implementation with print_json
- No real API integration

**After:**
- Uses `support_ticket_sdk.get_ticket()` to get SupportTicket object
- Converts SupportTicket object to dictionary
- Uses `UniversalOutputFormatter.render_get()` for consistent output
- Proper error handling for ticket not found

#### Support Ticket Create Command (`vantage_cli/commands/support_ticket/create.py`)
**Before:**
- Mock implementation with print_json
- No arguments, no real API integration

**After:**
- Uses `support_ticket_sdk.create_ticket()` with proper arguments
- Arguments: `--subject`, `--description`, `--priority` (optional, default="medium")
- Returns created SupportTicket object
- Uses `UniversalOutputFormatter.render_get()` to display created ticket
- Success message shown after creation

#### Support Ticket Update Command (`vantage_cli/commands/support_ticket/update.py`)
**Before:**
- Mock implementation with print_json
- Only ticket_id argument

**After:**
- Uses `support_ticket_sdk.update_ticket()` with optional fields
- Arguments: `ticket_id` (required), `--subject`, `--description`, `--status`, `--priority` (all optional)
- Returns updated SupportTicket object
- Uses `UniversalOutputFormatter.render_get()` to display updated ticket
- Success message shown after update

#### Support Ticket Delete Command (`vantage_cli/commands/support_ticket/delete.py`)
**Before:**
- Mock implementation with print_json
- No confirmation prompt

**After:**
- Uses `support_ticket_sdk.delete_ticket()` to delete ticket
- Arguments: `ticket_id` (required), `--force` to skip confirmation
- Confirmation prompt before deletion (unless --force used)
- Uses `UniversalOutputFormatter.render_get()` for JSON output
- Success message shown after deletion

#### Support Ticket Registration (`vantage_cli/main.py`)
**Added:**
- Import `support_ticket_app` from commands
- Register with `app.add_typer(support_ticket_app, name="support-ticket")`
- All commands now accessible via `vantage support-ticket <command>`

**Fixed:**
- Removed `-p` short flag from `--priority` options to avoid conflict with global `--profile` flag

## Benefits

### 1. Separation of Concerns
- **SDK**: Pure business logic, no UI dependencies
- **Commands**: Orchestration of SDK + formatting
- **UniversalOutputFormatter**: Consistent presentation across all commands

### 2. Consistency
- Same output patterns across all resource types (profiles, clusters, notebooks, jobs)
- Automatic JSON/table switching
- Standardized error handling
- Unified user experience

### 3. Maintainability
- Single source of truth for formatting logic
- Easy to update output format globally
- Reduced code duplication
- Clear architectural boundaries

### 4. Type Safety
- SDKs return strongly-typed objects (Cluster, Notebook, Profile)
- Commands convert to dicts only for presentation
- Better IDE support and error detection
- Easier testing and mocking

## Commands Not Refactored

### Cluster Delete (`vantage_cli/commands/cluster/delete.py`)
- **Reason**: Contains complex app deployment cleanup logic
- **Status**: Left as-is with existing RenderStepOutput
- **Future**: Will refactor when SDK implements delete operation

### Cluster Create (`vantage_cli/commands/cluster/create.py`)
- **Reason**: Complex workflow with app deployment
- **Status**: Not yet implemented in SDK
- **Future**: Will refactor when SDK implements create operation

### Notebook Create/Update/Delete
- **Status**: Not yet refactored
- **Reason**: These operations may involve complex workflows
- **Future**: Will evaluate refactoring needs after create/delete patterns are established

## Testing

### Verified Commands:

**Clusters:**
- ✅ `vantage cluster list --help`
- ✅ `vantage cluster get --help`
- ✅ `vantage cluster list` (empty result)
- ✅ Error handling (authentication errors displayed correctly)

**Notebooks:**
- ✅ `vantage notebook list --help`
- ✅ `vantage notebook get --help`
- ✅ `vantage notebook list` (empty result)
- ✅ `vantage notebook get test-notebook` (not found error)

**Jobs:**
- ✅ `vantage job script list --help`
- ✅ All job commands already using UniversalOutputFormatter

**Support Tickets:**
- ✅ `vantage support-ticket --help`
- ✅ `vantage support-ticket list --help`
- ✅ `vantage support-ticket get --help`
- ✅ `vantage support-ticket create --help`
- ✅ `vantage support-ticket update --help`
- ✅ `vantage support-ticket delete --help`
- ✅ No `-p` flag conflicts with global `--profile`

### Expected Behavior:
- Table output shows resources in formatted table
- JSON output returns proper JSON structure
- Boolean fields handled correctly (e.g., profile `is_active` shows green checkmark)
- Empty results display user-friendly messages
- Not found errors display clear error messages

## Related Files

### Modified:

- `vantage_cli/commands/cluster/list.py` - Refactored to use UniversalOutputFormatter
- `vantage_cli/commands/cluster/get.py` - Refactored to use UniversalOutputFormatter
- `vantage_cli/commands/notebook/list.py` - Refactored to use UniversalOutputFormatter
- `vantage_cli/commands/notebook/get.py` - Refactored to use UniversalOutputFormatter
- `vantage_cli/commands/support_ticket/list.py` - Refactored to use UniversalOutputFormatter
- `vantage_cli/commands/support_ticket/get.py` - Refactored to use UniversalOutputFormatter
- `vantage_cli/commands/support_ticket/create.py` - Refactored to use SDK + UniversalOutputFormatter
- `vantage_cli/commands/support_ticket/update.py` - Refactored to use SDK + UniversalOutputFormatter
- `vantage_cli/commands/support_ticket/delete.py` - Refactored to use SDK + UniversalOutputFormatter
- `vantage_cli/schemas.py` - Added Notebook and SupportTicket schemas
- `vantage_cli/main.py` - Registered support_ticket_app

### Created:

- `vantage_cli/sdk/notebook/` - New notebook SDK directory
- `vantage_cli/sdk/notebook/__init__.py` - SDK module init
- `vantage_cli/sdk/notebook/crud.py` - NotebookSDK with list and get operations
- `vantage_cli/sdk/support_ticket/` - New support ticket SDK directory
- `vantage_cli/sdk/support_ticket/__init__.py` - SDK module init
- `vantage_cli/sdk/support_ticket/crud.py` - SupportTicketSDK with full CRUD operations

### Unchanged (for now):
- `vantage_cli/commands/cluster/delete.py` - Complex cleanup logic, will refactor later
- `vantage_cli/commands/cluster/create.py` - Not yet implemented in SDK
- `vantage_cli/commands/cluster/render.py` - Can be deprecated once all commands refactored
- `vantage_cli/commands/notebook/render.py` - Can be deprecated once all commands refactored
- `vantage_cli/commands/notebook/create.py` - Not yet refactored
- `vantage_cli/commands/notebook/update.py` - Not yet refactored
- `vantage_cli/commands/notebook/delete.py` - Not yet refactored
- `vantage_cli/sdk/cluster/crud.py` - Already clean, no changes needed
- `vantage_cli/commands/job/**/*.py` - Already using UniversalOutputFormatter ✅

## Summary

### Completed Refactoring:

1. ✅ **Profile commands** - All CRUD operations use ProfileSDK + UniversalOutputFormatter
2. ✅ **Cluster list/get** - Use ClusterSDK + UniversalOutputFormatter  
3. ✅ **Notebook list/get** - Use NotebookSDK + UniversalOutputFormatter
4. ✅ **Job commands** - Already using UniversalOutputFormatter (no changes needed)
5. ✅ **Support Ticket commands** - Full CRUD operations use SupportTicketSDK + UniversalOutputFormatter

### Architecture Achieved:

- **SDK Layer**: Pure business logic returning Python objects
  - ProfileSDK, ClusterSDK, NotebookSDK, SupportTicketSDK
  - GraphQL-based for profiles/clusters/notebooks/support tickets
  - REST-based for job commands
  
- **Command Layer**: Thin orchestration layer
  - Calls SDK methods
  - Converts objects to dicts for presentation
  - Handles CLI arguments and options
  
- **Presentation Layer**: UniversalOutputFormatter
  - Consistent output across all commands
  - Automatic JSON/table switching
  - Standardized error messages
  - Boolean formatting (green checkmarks)

## Next Steps

1. ✅ Complete profile commands refactoring (done)
2. ✅ Complete cluster list/get commands refactoring (done)
3. ✅ Complete notebook list/get commands refactoring (done)
4. ✅ Verify job commands use UniversalOutputFormatter (done - already refactored)
5. ✅ Complete support ticket commands refactoring (done - full CRUD)
6. ⏳ Implement cluster create/delete in SDK
7. ⏳ Refactor cluster create/delete commands once SDK supports them
8. ⏳ Evaluate and refactor notebook create/update/delete commands
9. ⏳ Apply same pattern to other resource types (deployments, networks, etc.)
10. ⏳ Remove deprecated render.py modules once all commands refactored

## Architecture Pattern for Future Refactoring

### 1. Create SDK (if needed)
```python
# In vantage_cli/sdk/resource/crud.py

class ResourceSDK:
    """SDK for resource operations."""
    
    async def list_resources(self, ctx, filters=None) -> List[Resource]:
        """List resources using GraphQL/REST API."""
        # Execute query/request
        # Parse response
        # Return list of Resource objects
        
    async def get_resource(self, ctx, resource_id) -> Optional[Resource]:
        """Get single resource by ID."""
        # Execute query/request
        # Parse response
        # Return Resource object or None

# Create singleton instance
resource_sdk = ResourceSDK()
```

### 2. Create Schema (if needed)
```python
# In vantage_cli/schemas.py

class Resource(BaseModel):
    """Schema for resource data."""
    id: str
    name: str
    status: Optional[str] = None
    # ... other fields
```

### 3. Refactor Command
```python
# In vantage_cli/commands/resource/list.py

from vantage_cli.render import UniversalOutputFormatter
from vantage_cli.sdk.resource.crud import resource_sdk

@handle_abort
@attach_settings
async def list_resources(ctx: typer.Context):
    """List all resources."""
    # Create formatter
    formatter = UniversalOutputFormatter(
        console=ctx.obj.console,
        json_output=ctx.obj.json_output
    )
    
    try:
        # Use SDK to get resources
        resources = await resource_sdk.list_resources(ctx)
        
        # Convert to dict format for formatter
        resources_data = [
            {
                "id": r.id,
                "name": r.name,
                "status": r.status,
                # ... other fields
            }
            for r in resources
        ]
        
        # Render with formatter
        formatter.render_list(
            data=resources_data,
            resource_name="Resources",
            empty_message="No resources found."
        )
        
    except Abort:
        raise
    except Exception as e:
        logger.error(f"Error listing resources: {e}")
        formatter.render_error(
            error_message="Failed to list resources.",
            details={"error": str(e)}
        )
```

### 4. Refactor Get Command
```python
# In vantage_cli/commands/resource/get.py

@handle_abort
@attach_settings
async def get_resource(ctx: typer.Context, resource_id: str):
    """Get resource details."""
    formatter = UniversalOutputFormatter(
        console=ctx.obj.console,
        json_output=ctx.obj.json_output
    )
    
    try:
        # Use SDK to get resource
        resource = await resource_sdk.get_resource(ctx, resource_id)
        
        if not resource:
            formatter.render_error(
                error_message=f"Resource '{resource_id}' not found."
            )
            raise Abort(
                f"Resource '{resource_id}' not found.",
                subject="Resource Not Found",
                log_message=f"Resource '{resource_id}' not found",
            )
        
        # Convert to dict
        resource_data = {
            "id": resource.id,
            "name": resource.name,
            "status": resource.status,
            # ... other fields
        }
        
        # Render with formatter
        formatter.render_get(
            data=resource_data,
            resource_name="Resource",
            resource_id=resource_id
        )
        
    except Abort:
        raise
    except Exception as e:
        logger.error(f"Error getting resource: {e}")
        formatter.render_error(
            error_message="Failed to get resource.",
            details={"error": str(e)}
        )
```

### Key Principles:
1. **SDK returns objects, not dicts** - Use Pydantic models for type safety
2. **Commands convert to dicts only for presentation** - Keep objects in SDK layer
3. **Use UniversalOutputFormatter for all output** - Table, JSON, errors
4. **Consistent error handling** - Try/except with formatter.render_error()
5. **No GraphQL/REST logic in commands** - Keep in SDK layer
6. **Clean separation of concerns** - SDK (logic) → Command (orchestration) → Formatter (presentation)

This pattern ensures:
- Clean separation of concerns
- Consistent user experience across all commands
- Easy testing and maintenance
- Type-safe data flow
- Reusable SDK components
