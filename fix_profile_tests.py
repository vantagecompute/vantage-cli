#!/usr/bin/env python3
"""Script to fix profile CRUD tests by applying json_output parameter removal pattern."""

import re

def fix_profile_tests():
    file_path = "tests/unit/test_profile_crud.py"
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Add SimpleNamespace import if not present
    if "from types import SimpleNamespace" not in content:
        content = content.replace(
            "from unittest.mock import Mock, patch",
            "from types import SimpleNamespace\nfrom unittest.mock import Mock, patch"
        )
    
    # Fix mock_context fixtures
    fixture_pattern = r'(ctx\.obj = Mock\(\)[^}]+ctx\.obj\.profile = "[^"]+")[^}]*(return ctx)'
    fixture_replacement = '''ctx.obj = SimpleNamespace(
            profile="default",
            verbose=False,
            json_output=False
        )
        return ctx'''
    
    content = re.sub(fixture_pattern, fixture_replacement, content, flags=re.MULTILINE | re.DOTALL)
    
    # Fix function calls - remove json_output parameters
    function_patterns = [
        (r'create_profile\(([^,]+), ([^,]+), ([^,]+), ([^,]+), json_output=(\w+)\)', r'mock_ctx.obj.json_output = \5\n        create_profile(\1, \2, \3, \4)'),
        (r'delete_profile\(([^,]+), ([^,]+), json_output=(\w+)\)', r'mock_ctx.obj.json_output = \3\n        delete_profile(\1, \2)'),
        (r'get_profile\(([^,]+), ([^,]+), json_output=(\w+)\)', r'mock_ctx.obj.json_output = \3\n        get_profile(\1, \2)'),
        (r'list_profiles\(([^,]+), json_output=(\w+)\)', r'mock_ctx.obj.json_output = \2\n        list_profiles(\1)'),
        (r'use_profile\(([^,]+), ([^,]+), json_output=(\w+)\)', r'mock_ctx.obj.json_output = \3\n        use_profile(\1, \2)'),
    ]
    
    for pattern, replacement in function_patterns:
        content = re.sub(pattern, replacement, content)
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("Profile CRUD tests fixed!")

if __name__ == "__main__":
    fix_profile_tests()