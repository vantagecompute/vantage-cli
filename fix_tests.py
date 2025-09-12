#!/usr/bin/env python3
"""Script to fix all unit test files that have json_output parameter issues."""

import re
import glob
import os

def fix_test_file(filepath):
    """Fix a single test file."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Add SimpleNamespace import if not present
    if 'from types import SimpleNamespace' not in content:
        # Find the import section and add SimpleNamespace
        import_match = re.search(r'(from unittest\.mock import [^\n]+)', content)
        if import_match:
            old_import = import_match.group(1)
            new_import = old_import.replace('from unittest.mock import', 'from types import SimpleNamespace\nfrom unittest.mock import')
            content = content.replace(old_import, new_import)
    
    # Fix json_output function calls
    # Pattern: function_name(ctx, json_output=True/False)
    # Replace with: ctx.obj.json_output = True/False\n        function_name(ctx)
    patterns = [
        (r'(\s+)(await\s+)?(\w+)\(([^,]+),\s*json_output=True\)', 
         r'\1\2\3.obj.json_output = True\n\1\2\3(\4)'),
        (r'(\s+)(await\s+)?(\w+)\(([^,]+),\s*json_output=False\)', 
         r'\1\2\3.obj.json_output = False\n\1\2\3(\4)'),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    # Fix context fixtures to use SimpleNamespace
    # Pattern: ctx.obj = Mock()
    if 'ctx.obj = Mock()' in content:
        content = content.replace(
            'ctx.obj = Mock()',
            'ctx.obj = SimpleNamespace(\n        profile=None,\n        verbose=False,\n        json_output=False\n    )'
        )
    
    # Write back the file
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"Fixed {filepath}")

def main():
    """Main function."""
    # Find all test files that likely have json_output issues
    test_files = [
        'tests/unit/test_apps_list_command.py',
        'tests/unit/test_cluster_commands.py', 
        'tests/unit/test_config_commands.py',
        'tests/unit/test_federation_commands.py',
        'tests/unit/test_profile_crud.py',
        'tests/unit/test_profile_crud_extra.py',
    ]
    
    for filepath in test_files:
        if os.path.exists(filepath):
            fix_test_file(filepath)
        else:
            print(f"File not found: {filepath}")

if __name__ == '__main__':
    main()