# Plural Aliases for Job and License Commands

## Overview

Plural aliases have been added to all job and license subcommands for improved CLI ergonomics. Users can now use natural plural forms as shortcuts to directly call the `list` command for each resource type.

**Key Feature**: `vantage job scripts` is equivalent to `vantage job script list`

## Implementation

The plural aliases are registered at the parent command level (`job_app` and `license_app`) using the `.command()` method to directly register the list functions with `hidden=True`. This approach:

1. Makes plural aliases direct shortcuts to list commands (e.g., `vantage job scripts` = `vantage job script list`)
2. Keeps them hidden from help text to avoid confusion
3. Provides a more intuitive CLI experience for listing resources

## Job Command Aliases

All job resource types now support plural aliases that directly invoke the `list` command:

| Resource   | Standard Command           | Plural Alias (= list)   |
|------------|----------------------------|-------------------------|
| script     | `vantage job script list`  | `vantage job scripts`   |
| template   | `vantage job template list`| `vantage job templates` |
| submission | `vantage job submission list`| `vantage job submissions` |

### Job Examples

```bash
# These are equivalent:
vantage job script list
vantage job scripts

# These are equivalent:
vantage job template list --limit 10
vantage job templates --limit 10

# These are equivalent:
vantage job submission list --user-only
vantage job submissions --user-only
```

## License Command Aliases

All license resource types now support plural aliases that directly invoke the `list` command:

| Resource      | Standard Command                  | Plural Alias (= list)         |
|---------------|-----------------------------------|-------------------------------|
| server        | `vantage license server list`     | `vantage license servers`     |
| feature       | `vantage license feature list`    | `vantage license features`    |
| product       | `vantage license product list`    | `vantage license products`    |
| configuration | `vantage license configuration list` | `vantage license configurations` |
| booking       | `vantage license booking list`    | `vantage license bookings`    |
| deployment    | `vantage license deployment list` | `vantage license deployments` |

### License Examples

```bash
# These are equivalent:
vantage license server list
vantage license servers

# These are equivalent:
vantage license configuration list --limit 20
vantage license configurations --limit 20

# These are equivalent:
vantage license feature list --search "matlab"
vantage license features --search "matlab"
```

## Technical Details

### Code Structure

The plural aliases are registered in two files by directly registering the list functions:

1. **`vantage_cli/commands/job/__init__.py`**

   ```python
   # Import list functions
   from .script.list import list_job_scripts
   from .submission.list import list_job_submissions
   from .template.list import list_job_templates
   
   # Add plural aliases that directly call the list commands (hidden from help)
   job_app.command("scripts", hidden=True)(list_job_scripts)
   job_app.command("submissions", hidden=True)(list_job_submissions)
   job_app.command("templates", hidden=True)(list_job_templates)
   ```

2. **`vantage_cli/commands/license/__init__.py`**

   ```python
   # Import list functions
   from .booking.list import list_bookings
   from .server.list import list_license_servers
   from .product.list import list_license_products
   from .configuration.list import list_license_configurations
   from .deployment.list import list_license_deployments
   from .feature.list import list_license_features
   
   # Add plural aliases that directly call the list commands (hidden from help)
   license_app.command("bookings", hidden=True)(list_bookings)
   license_app.command("servers", hidden=True)(list_license_servers)
   license_app.command("products", hidden=True)(list_license_products)
   license_app.command("configurations", hidden=True)(list_license_configurations)
   license_app.command("deployments", hidden=True)(list_license_deployments)
   license_app.command("features", hidden=True)(list_license_features)
   ```

### Hidden from Help

The `hidden=True` parameter ensures that these aliases don't clutter the help output. When users run `vantage job --help` or `vantage license --help`, they only see the canonical singular forms.

### Direct List Command Aliases

The plural aliases are **direct shortcuts to the list command only**:

- ✅ `vantage job scripts` → Runs `list_job_scripts()` directly
- ✅ `vantage license servers --limit 10` → Runs `list_license_servers()` with options
- ❌ `vantage job scripts get 123` → Not supported (plural is list-only)

To access other operations (get, create, update, delete), use the full singular form:
- `vantage job script get 123`
- `vantage job script create --name "test"`
- `vantage license server update 456 --port 8080`

## Benefits

1. **Improved UX**: Users can type `vantage job scripts` instead of `vantage job script list` - more natural and faster
2. **Backward Compatible**: Original singular commands still work exactly as before
3. **Clean Help Output**: Hidden aliases don't add noise to help text
4. **Consistent Pattern**: Same approach used across all job and license resources
5. **List-Only Shortcuts**: Plural forms are dedicated to listing, keeping the interface intuitive

## Testing

All plural aliases have been tested and verified to work correctly as direct list command shortcuts:

```bash
# Job commands - all show list command help
✅ vantage job scripts --help          # "List all job scripts"
✅ vantage job templates --help        # "List all job templates"
✅ vantage job submissions --help      # "List all job submissions"

# License commands - all show list command help
✅ vantage license servers --help           # "List all license servers"
✅ vantage license features --help          # "List all license features"
✅ vantage license products --help          # "List all license products"
✅ vantage license configurations --help    # "List all license configurations"
✅ vantage license bookings --help          # "List all license bookings"
✅ vantage license deployments --help       # "List all license deployments"
```

All aliases are properly hidden from help output while remaining fully functional as list command shortcuts.
