#!/usr/bin/env python3
"""Script to fix cluster tests by applying json_output parameter removal pattern."""

import re

def fix_cluster_tests():
    file_path = "tests/unit/test_cluster_commands.py"
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Add SimpleNamespace import if not present
    if "from types import SimpleNamespace" not in content:
        content = content.replace(
            "from unittest.mock import Mock, patch",
            "from types import SimpleNamespace\nfrom unittest.mock import Mock, patch"
        )
    
    # Fix mock_context fixtures
    fixture_pattern = r'(ctx\.obj = Mock\(\)\s+ctx\.obj\.settings = Mock\(\)\s+ctx\.obj\.profile = "default")'
    fixture_replacement = 'ctx.obj = SimpleNamespace(\n            profile="default",\n            verbose=False,\n            json_output=False\n        )'
    
    content = re.sub(fixture_pattern, fixture_replacement, content, flags=re.MULTILINE)
    
    # Fix function calls - remove json_output parameters
    patterns_to_fix = [
        (r'list_clusters\(([^,]+), json_output=\w+\)', r'list_clusters(\1)'),
        (r'delete_cluster\(([^,]+), ([^,]+), force=(\w+), json_output=\w+\)', r'delete_cluster(\1, \2, force=\3)'),
        (r'get_cluster\(([^,]+), ([^,]+), json_output=\w+\)', r'get_cluster(\1, \2)'),
    ]
    
    for pattern, replacement in patterns_to_fix:
        content = re.sub(pattern, replacement, content)
    
    # Add context setting before function calls for json_output tests
    content = re.sub(
        r'(mock_get_effective_json_output\.return_value = True)\s+(# Call the function)',
        r'\1\n        mock_ctx.obj.json_output = True\n        \2',
        content,
        flags=re.MULTILINE
    )
    
    # Handle cases where json_output is False
    content = re.sub(
        r'(await list_clusters\(mock_ctx\))\s+(# Check that render_json was called)',
        r'mock_ctx.obj.json_output = True\n        \1\n        \2',
        content,
        flags=re.MULTILINE
    )
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("Cluster tests fixed!")

if __name__ == "__main__":
    fix_cluster_tests()