# UniversalOutputFormatter - Centralized CLI Output Management

## Overview

The new `UniversalOutputFormatter` class provides a centralized way to handle output formatting across all CLI commands, eliminating code duplication and providing consistent formatting.

## Before (Manual Table Creation)

Every command had to manually handle JSON vs table output:

```python
# OLD WAY - Every command needs this boilerplate
if ctx.obj.json_output:
    print_json(data=scripts_data)
else:
    scripts = scripts_data.get("results", [])
    if not scripts:
        typer.echo("No job scripts found.")
        return
        
    table = Table(title="Job Scripts", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan", min_width=8)
    table.add_column("Name", style="green", min_width=20)
    table.add_column("Owner", style="blue", min_width=15)
    table.add_column("Description", style="white", min_width=30)
    table.add_column("Template ID", style="yellow", min_width=10)
    table.add_column("Created", style="dim", min_width=10)
    table.add_column("Archived", style="red", min_width=8)
    
    for script in scripts:
        table.add_row(
            str(script.get("id", "")),
            script.get("name", ""),
            script.get("owner", ""),
            script.get("description", "")[:50] + "..." if len(script.get("description", "")) > 50 else script.get("description", ""),
            str(script.get("job_script_template_id", "")),
            script.get("created_at", "").split("T")[0] if script.get("created_at") else "",
            "Yes" if script.get("archived") else "No"
        )
    
    ctx.obj.console.print(table)
```

## After (UniversalOutputFormatter)

Clean, consistent output with automatic formatting:

```python
# NEW WAY - Simple and clean
formatter = UniversalOutputFormatter(console=ctx.obj.console, json_output=ctx.obj.json_output)
formatter.output(data=scripts_data, title="Job Scripts")
```

## Key Features

### 1. Automatic Data Structure Detection
- **Paginated responses**: Automatically detects `{"items": [...]}` or `{"results": [...]}` structures
- **Single items**: Renders individual objects as key-value tables
- **Lists**: Creates column-based tables from list data
- **Simple values**: Direct output for strings/numbers

### 2. Smart Column Generation
- **Dynamic columns**: Automatically detects all unique keys across data items
- **Intelligent ordering**: Common fields (id, name, description, etc.) appear first
- **Consistent headers**: Formats snake_case to "Title Case" automatically
- **Type-based styling**: Different colors for IDs, names, dates, status fields

### 3. Built-in Value Formatting
- **Dates**: Automatically formats `created_at`/`updated_at` timestamps
- **Booleans**: Converts `true/false` to "Yes/No"
- **Long text**: Automatically truncates descriptions with ellipsis
- **Null handling**: Shows "N/A" for missing values
- **Numbers**: Proper formatting for IDs and numeric fields

### 4. Pagination Support
- **Page info**: Automatically shows "Page X of Y (Total: Z)" when pagination data exists
- **Consistent display**: Same pagination format across all commands

## Migration Benefits

### Code Reduction
- **Before**: ~40 lines of table creation code per command
- **After**: 2 lines total
- **Reduction**: 95% less code per command

### Consistency
- **Unified styling**: All tables use the same color scheme and formatting
- **Standardized empty states**: Consistent "No items found" messages
- **Predictable output**: Users get the same experience across all commands

### Maintainability
- **Single source of truth**: All formatting logic in one place
- **Easy updates**: Change formatting globally by updating one class
- **Bug fixes**: Fix display issues once, applies everywhere

## Example Commands to Update

All of these commands can be simplified using the new formatter:

1. **Job Commands** (15 files):
   - `job/script/list.py` ✅ **UPDATED**
   - `job/script/get.py`
   - `job/template/list.py`
   - `job/submission/list.py`
   - And 11 more...

2. **License Commands** (20+ files):
   - `license/feature/list.py`
   - `license/product/list.py`
   - `license/server/list.py`
   - And 17+ more...

## Next Steps

1. **Update remaining job commands** to use UniversalOutputFormatter
2. **Migrate license commands** to the new pattern
3. **Remove old table creation code** once migration is complete
4. **Add advanced features** like custom column configs if needed

The UniversalOutputFormatter represents a significant improvement in code maintainability and user experience consistency across the entire CLI application.