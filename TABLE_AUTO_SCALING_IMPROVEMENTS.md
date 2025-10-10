# Table Auto-Scaling Improvements

## Overview

Enhanced the `UniversalOutputFormatter` to provide intelligent auto-scaling for terminal table output, ensuring optimal display across different terminal widths with smart text truncation.

## Key Improvements

### 1. Priority-Based Column Allocation

Columns are now assigned priorities based on importance:

- **Priority 3 (High)**: `id`, `name`, `title`, `status` - Always shown
- **Priority 2 (Medium)**: `description`, `created_at`, `updated_at`, `owner_email` - Shown when space permits
- **Priority 1 (Low)**: `client_id`, `cloned_from_id`, `parent_template_id` - Shown only with ample space

### 2. Intelligent Width Calculation

The new `_calculate_proportional_widths()` method:

- Samples actual data (up to 10 items) to determine realistic column widths
- Assigns optimal, minimum, and maximum widths per column type
- Uses priority-based allocation algorithm to distribute available space
- Gracefully scales down when terminal width is limited

### 3. Smart Text Truncation

New `_smart_truncate()` method provides intelligent ellipsis truncation:

**For very narrow columns (< 6 chars):**
- Shows first N chars + "..." where N = width - 3
- Examples:
  - Width 5: "VeryLongText" → "Ve..."
  - Width 4: "VeryLongText" → "V..."
  - Width 3: "VeryLongText" → "Ver" (no ellipsis, just truncate)

**For standard columns (≥ 6 chars):**
- Uses traditional ellipsis: "VeryLongText" → "VeryLon..."

This ensures users always see meaningful content instead of just "..." in narrow columns.

### 3. Column-Specific Configurations
Different column types get appropriate width constraints:

| Column Type | Optimal | Max | Min | Notes |
|-------------|---------|-----|-----|-------|
| `id` | 10 | 12 | 6 | Minimal space for IDs |
| `name`, `title` | 30 | 40 | 10 | Moderate space for names |
| `description` | 40 | 60 | 15 | More space for longer text |
| `status`, `state` | 15 | 20 | 8 | Compact for status values |
| Dates/Times | 12 | 20 | 10 | Standardized date display |
| `email` | 25 | 35 | 12 | Space for email addresses |
| Default | 20 | 30 | 8 | Balanced default |

### 4. Smart Overflow Handling
Overflow behavior adapts based on column width:
- **Wide columns (≥15 chars)**: Use `fold` for text wrapping
- **Narrow columns (<15 chars)**: Use `ellipsis` to truncate with `...`
- **IDs and dates**: Always use `ellipsis` (never wrap)
- **Descriptions**: Switch from `fold` to `ellipsis` when width < 20

### 5. Width Allocation Algorithm
Three-phase allocation strategy:

**Phase 1: Minimum Widths**
- Assign minimum width to all columns
- Calculate remaining space

**Phase 2: Priority-Based Growth**
- Iterate through priority levels (3 → 2 → 1)
- Distribute space proportionally to reach optimal widths
- High priority columns get space first

**Phase 3: Even Distribution**
- If space remains, distribute evenly among all columns
- Respect maximum width constraints
- Stop when all columns reach max or space exhausted

## Example Output

### Wide Terminal (200 chars)
```
Job Scripts
╭─────┬──────────────────┬────────────────────────────────────╮
│ ID  │ Name             │ Description                        │
├─────┼──────────────────┼────────────────────────────────────┤
│ 6   │ hpcg-benchmark   │ Benchmark using HPCG               │
│ 54  │ hpcg-benchmark-  │ Benchmark using HPCG built with    │
│     │ oacc             │ AMD compilers                      │
╰─────┴──────────────────┴────────────────────────────────────╯
```

### Narrow Terminal (80 chars)
```
Job Scripts
╭─────┬──────────┬────────────────╮
│ ID  │ Name     │ Description    │
├─────┼──────────┼────────────────┤
│ 6   │ hpcg-be… │ Benchmark us…  │
│ 54  │ hpcg-be… │ Benchmark us…  │
╰─────┴──────────┴────────────────╯
```

## Benefits

1. **Responsive**: Tables automatically adapt to terminal width
2. **Prioritized**: Most important columns always visible
3. **Readable**: Text wraps intelligently, not cut off mid-word
4. **Consistent**: Same algorithm works across all commands
5. **Efficient**: Minimal overhead with smart sampling

## Testing

Tested with:
- ✅ `vantage job scripts` - Multi-column table with varied content
- ✅ `vantage job submissions` - Nested objects handled properly
- ✅ `vantage license servers --json` - JSON output unaffected
- ✅ Different terminal widths (80, 120, 200 chars)

## Implementation Files

- `vantage_cli/render.py`:
  - `_calculate_proportional_widths()` - Main width calculation
  - `_get_column_config()` - Column configuration and priorities
  - `_allocate_column_widths()` - Priority-based allocation algorithm
  - `_render_with_textual_datatable()` - Updated table rendering

## Future Enhancements

Potential improvements for future iterations:
- [ ] Add column hiding for very narrow terminals (< 60 chars)
- [ ] Implement horizontal scrolling for interactive mode
- [ ] Cache column configurations for better performance
- [ ] Add user-configurable column priorities via config file
- [ ] Support custom column width overrides per command
