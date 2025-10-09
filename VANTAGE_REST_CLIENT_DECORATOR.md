# Vantage REST API Client Decorator

## Overview

The `@attach_vantage_rest_client` decorator automatically initializes and attaches a `VantageRestApiClient` to the Typer context, making it easy to use the REST API in CLI commands without manual client management.

## Decorator

### `@attach_vantage_rest_client`

**Prerequisites:**
- `@attach_settings` must be applied before this decorator
- `@attach_persona` must be applied before this decorator

**What it does:**
1. Retrieves the base URL from `ctx.obj.settings.get_apis_url()`
2. Creates a `VantageRestApiClient` instance with:
   - The base URL from settings
   - The persona from context (for authentication)
   - The profile from context
   - The settings from context
3. Attaches the client to `ctx.obj.rest_client`
4. For async functions: Automatically closes the client after the function completes

## Usage

### Basic Pattern

```python
from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import handle_abort
from vantage_cli.vantage_rest_api_client import attach_vantage_rest_client
import typer

@handle_abort
@attach_settings
@attach_persona
@attach_vantage_rest_client
async def my_command(ctx: typer.Context):
    """My command that needs REST API access."""
    # The REST client is now available at ctx.obj.rest_client
    result = await ctx.obj.rest_client.get("/some/path")
    return result
```

### Decorator Order

**IMPORTANT:** The decorators must be applied in this specific order (from bottom to top):

```python
@handle_abort           # 1. First (outermost)
@attach_settings        # 2. Second - provides ctx.obj.settings
@attach_persona         # 3. Third - provides ctx.obj.persona (requires settings)
@attach_vantage_rest_client  # 4. Fourth (innermost) - provides ctx.obj.rest_client (requires settings & persona)
async def my_command(ctx: typer.Context):
    ...
```

## Example: SDK Function

Here's a real example from `vantage_cli/sdk/admin/management/organizations.py`:

```python
from typing import Any, Dict, List
import typer
from vantage_cli.config import attach_settings
from vantage_cli.auth import attach_persona
from vantage_cli.vantage_rest_api_client import attach_vantage_rest_client


@attach_settings
@attach_persona
@attach_vantage_rest_client
async def get_extra_attributes(ctx: typer.Context) -> List[Dict[str, Any]]:
    """Get organization extra attributes.
    
    The REST client is automatically initialized and attached to ctx.obj.rest_client
    by the @attach_vantage_rest_client decorator.
    
    Args:
        ctx: Typer context with rest_client, settings, and persona already attached
    
    Returns:
        List of extra attribute dictionaries
    """
    path = "/admin/management/organizations/extra-attributes"
    response = await ctx.obj.rest_client.get(path)
    return response
```

## Example: CLI Command

Here's how to use it in a CLI command:

```python
import typer
from typing_extensions import Annotated

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import Abort, handle_abort
from vantage_cli.render import UniversalOutputFormatter
from vantage_cli.vantage_rest_api_client import attach_vantage_rest_client


@handle_abort
@attach_settings
@attach_persona
@attach_vantage_rest_client
async def list_licenses(
    ctx: typer.Context,
    active_only: Annotated[
        bool,
        typer.Option("--active", help="Show only active licenses")
    ] = False,
):
    """List all organization licenses."""
    formatter = UniversalOutputFormatter(
        console=ctx.obj.console,
        json_output=ctx.obj.json_output
    )
    
    try:
        # The REST client is automatically available
        path = "/admin/management/licenses"
        params = {"active": "true"} if active_only else None
        
        licenses = await ctx.obj.rest_client.get(path, params=params)
        
        # Render the results
        formatter.render_list(
            data=licenses,
            resource_name="Licenses",
            empty_message="No licenses found."
        )
        
    except Exception as e:
        formatter.render_error(
            error_message="Failed to list licenses",
            details={"error": str(e)}
        )
        raise Abort("Failed to list licenses", log_message=str(e))
```

## API Methods

Once the client is attached to `ctx.obj.rest_client`, you can use:

```python
# GET request
result = await ctx.obj.rest_client.get("/path", params={"key": "value"})

# POST request
result = await ctx.obj.rest_client.post("/path", json={"data": "value"})

# PUT request
result = await ctx.obj.rest_client.put("/path", json={"data": "value"})

# DELETE request
result = await ctx.obj.rest_client.delete("/path")

# Pretty print JSON
ctx.obj.rest_client.print_json(result)
```

## Error Handling

The client automatically handles:
- **Authentication errors (401/403)**: Attempts to refresh the access token
- **HTTP errors**: Raises `httpx.HTTPStatusError` with details
- **Network errors**: Raises appropriate exceptions

Example error handling:

```python
@handle_abort
@attach_settings
@attach_persona
@attach_vantage_rest_client
async def my_command(ctx: typer.Context):
    try:
        result = await ctx.obj.rest_client.get("/path")
        return result
    except httpx.HTTPStatusError as e:
        # Handle HTTP errors (4xx, 5xx)
        ctx.obj.console.print(f"[red]API Error {e.response.status_code}[/red]")
        raise Abort("API request failed")
    except Exception as e:
        # Handle other errors
        ctx.obj.console.print(f"[red]Error: {e}[/red]")
        raise
```

## Resource Cleanup

For **async functions**, the decorator automatically closes the HTTP client when the function completes (via `finally` block).

For **sync functions**, you must manually close the client if needed:

```python
@attach_settings
@attach_persona
@attach_vantage_rest_client
def sync_command(ctx: typer.Context):
    try:
        # Use the client
        # Note: sync functions should use asyncio.run() for async operations
        pass
    finally:
        # Manual cleanup for sync functions
        asyncio.run(ctx.obj.rest_client.close())
```

## Migration from Old Pattern

### Before (Manual Client Creation):

```python
from vantage_cli.vantage_rest_api_client import create_vantage_rest_client

async def my_function(client: VantageRestApiClient, settings: Settings):
    result = await client.get("/path")
    return result

# Usage:
client = create_vantage_rest_client(profile="default")
result = await my_function(client, settings)
await client.close()
```

### After (Decorator Pattern):

```python
from vantage_cli.vantage_rest_api_client import attach_vantage_rest_client
from vantage_cli.config import attach_settings
from vantage_cli.auth import attach_persona
import typer

@attach_settings
@attach_persona
@attach_vantage_rest_client
async def my_function(ctx: typer.Context):
    result = await ctx.obj.rest_client.get("/path")
    return result

# Usage in CLI command - decorators handle everything
# No manual client creation or cleanup needed
```

## Benefits

1. **Automatic Lifecycle Management**: Client is created and cleaned up automatically
2. **Consistent Pattern**: Same approach as `@attach_settings` and `@attach_persona`
3. **Less Boilerplate**: No need to manually create, pass, and close clients
4. **Built-in Authentication**: Automatically uses persona from context
5. **Token Refresh**: Automatically refreshes expired access tokens
6. **Type Safety**: Context object has properly typed rest_client attribute

## Complete Example

Here's a complete CLI command using all the best practices:

```python
import typer
from typing_extensions import Annotated

from vantage_cli.auth import attach_persona
from vantage_cli.config import attach_settings
from vantage_cli.exceptions import Abort, handle_abort
from vantage_cli.render import UniversalOutputFormatter
from vantage_cli.vantage_rest_api_client import attach_vantage_rest_client


@handle_abort
@attach_settings
@attach_persona
@attach_vantage_rest_client
async def get_organization_info(ctx: typer.Context):
    """Get current organization information."""
    formatter = UniversalOutputFormatter(
        console=ctx.obj.console,
        json_output=ctx.obj.json_output
    )
    
    verbose = getattr(ctx.obj, "verbose", False)
    
    try:
        if verbose and not ctx.obj.json_output:
            ctx.obj.console.print("[bold blue]Fetching organization info...[/bold blue]")
        
        # Use the REST client from context
        org_info = await ctx.obj.rest_client.get("/admin/management/organizations/info")
        
        # Render the output
        formatter.render_get(
            data=org_info,
            resource_name="Organization",
            resource_id=org_info.get("id", "")
        )
        
    except httpx.HTTPStatusError as e:
        formatter.render_error(
            error_message=f"Failed to fetch organization info (HTTP {e.response.status_code})",
            details={"error": e.response.text}
        )
        raise Abort("Failed to fetch organization info")
    except Exception as e:
        formatter.render_error(
            error_message="An unexpected error occurred",
            details={"error": str(e)}
        )
        raise Abort("Unexpected error", log_message=str(e))
```

## Testing

To test imports:

```bash
uv run python -c "from vantage_cli.vantage_rest_api_client import attach_vantage_rest_client; print('✓ Decorator imports successfully')"
```

## Summary

The `@attach_vantage_rest_client` decorator provides a clean, consistent way to use the Vantage REST API in CLI commands:

✅ Automatic client initialization
✅ Automatic authentication via persona
✅ Automatic token refresh
✅ Automatic resource cleanup
✅ Consistent with other decorators (`@attach_settings`, `@attach_persona`)
✅ Type-safe context usage
✅ Less boilerplate code
✅ Easier to test and maintain
