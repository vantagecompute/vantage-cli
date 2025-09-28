# UniversalOutputFormatter CRUD Operations Guide

## Overview

The `UniversalOutputFormatter` class now includes specialized render functions for all CRUD operations (Create, Read, Update, Delete), providing consistent output patterns across the entire CLI.

## Available CRUD Render Functions

### 1. `render_list()` - For LIST operations
```python
# List job scripts
formatter = UniversalOutputFormatter(console=ctx.obj.console, json_output=ctx.obj.json_output)
formatter.render_list(
    data=response_data,
    resource_name="Job Scripts",
    empty_message="No job scripts found."  # Optional
)
```

### 2. `render_get()` - For GET operations
```python
# Get specific job script
formatter.render_get(
    data=script_data,
    resource_name="Job Script",
    resource_id="123"  # Optional
)
```

### 3. `render_create()` - For CREATE operations
```python
# Create new job script
formatter.render_create(
    data=new_script_data,
    resource_name="Job Script",
    success_message="Custom success message"  # Optional
)
```

### 4. `render_update()` - For UPDATE operations
```python
# Update job script
formatter.render_update(
    data=updated_script_data,
    resource_name="Job Script",
    resource_id="123",  # Optional
    success_message="Custom update message"  # Optional
)
```

### 5. `render_delete()` - For DELETE operations
```python
# Delete job script
formatter.render_delete(
    resource_name="Job Script",
    resource_id="123",  # Optional
    success_message="Custom delete message",  # Optional
    data=response_data  # Optional - for APIs that return data on delete
)
```

## Additional Specialized Functions

### Error Handling
```python
# Render error information
formatter.render_error(
    error_message="Failed to create job script",
    details={"validation_errors": ["Name is required", "Template ID invalid"]}
)
```

### Confirmation Prompts
```python
# Render confirmation for destructive operations
formatter.render_confirmation(
    message="Are you sure you want to delete this job script?",
    resource_name="Job Script",
    resource_id="123"
)
```

### Operation Status (for long-running operations)
```python
# Render status of operations like deployments
formatter.render_operation_status(
    operation="Deployment",
    resource_name="Application Stack",
    status="In Progress",
    details="Provisioning infrastructure..."
)
```

### Bulk Operations
```python
# Render results of bulk operations
formatter.render_bulk_operation(
    operation="Bulk Delete",
    results={
        "total": 10,
        "success": 8,
        "failed": 2,
        "details": [
            {"id": "1", "success": True, "message": "Deleted successfully"},
            {"id": "2", "success": False, "message": "Permission denied"}
        ]
    },
    resource_name="Job Scripts"
)
```

### Validation Results
```python
# Render validation results
formatter.render_validation_results({
    "valid": False,
    "errors": ["Name must be unique", "Template not found"],
    "warnings": ["Description is recommended"]
})
```

## Migration Examples

### Before (Manual Output)
```python
# OLD WAY - Each command handles output manually
if ctx.obj.json_output:
    print_json(data=script_data)
else:
    if script_data:
        console.print("✅ Job script created successfully", style="green")
        table = Table(title="Created Script")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")
        for key, value in script_data.items():
            table.add_row(key, str(value))
        console.print(table)
    else:
        console.print("❌ Failed to create job script", style="red")
```

### After (Using UniversalOutputFormatter)
```python
# NEW WAY - Simple, consistent, semantic
formatter = UniversalOutputFormatter(console=ctx.obj.console, json_output=ctx.obj.json_output)
formatter.render_create(script_data, "Job Script")
```

## Command-Specific Usage Patterns

### Job Script Commands
```python
# List job scripts
formatter.render_list(scripts_data, "Job Scripts")

# Get job script
formatter.render_get(script_data, "Job Script", script_id)

# Create job script
formatter.render_create(new_script, "Job Script")

# Update job script  
formatter.render_update(updated_script, "Job Script", script_id)

# Delete job script
formatter.render_delete("Job Script", script_id)
```

### License Commands
```python
# List license features
formatter.render_list(features_data, "License Features")

# Get license server
formatter.render_get(server_data, "License Server", server_id)

# Create license product
formatter.render_create(new_product, "License Product")
```

## Output Examples

### List Operation (Table Mode)
```
License Features
┏━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ ID   ┃ Name                 ┃ Description                                                                                  ┃
┡━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 1    │ GPU Acceleration     │ Enables GPU-accelerated compute workloads                                                   │
│ 2    │ High Memory          │ Access to high-memory compute nodes                                                         │
└──────┴──────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────┘

Page 1 of 3 (Total: 15)
```

### Create Operation (Success)
```
✅ License Feature created successfully (ID: 123)

📋 Created Resource Details:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Field                                                                                                                                                                                                                ┃ Value                                                                                                                                                                                                                ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ id                                                                                                                                                                                                                   │ 123                                                                                                                                                                                                                  │
│ name                                                                                                                                                                                                                 │ GPU Acceleration                                                                                                                                                                                                     │
│ description                                                                                                                                                                                                          │ Enables GPU-accelerated compute workloads                                                                                                                                                                           │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Error Operation
```
❌ Failed to create license feature

📋 Error Details:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Field                                                                                                                                                                                                                ┃ Value                                                                                                                                                                                                                ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ error_code                                                                                                                                                                                                           │ VALIDATION_ERROR                                                                                                                                                                                                     │
│ message                                                                                                                                                                                                              │ Name must be unique                                                                                                                                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Benefits

1. **Consistency**: All operations follow the same output patterns
2. **Semantic Clarity**: Function names clearly indicate their purpose
3. **Automatic Formatting**: Handles JSON vs table output automatically
4. **Rich Visual Feedback**: Uses icons and colors for better UX
5. **Error Handling**: Consistent error display across all operations
6. **Reduced Code**: Single function call replaces 20-40 lines of output code
7. **Maintainability**: Update display logic once, applies everywhere

## Next Steps

1. **Update all job commands** to use appropriate CRUD render functions
2. **Migrate license commands** to use the new patterns  
3. **Remove manual table/JSON handling** from individual commands
4. **Standardize error handling** using `render_error()`
5. **Add custom validation** using `render_validation_results()`

The CRUD render functions provide a complete toolkit for consistent, professional CLI output across all operations.