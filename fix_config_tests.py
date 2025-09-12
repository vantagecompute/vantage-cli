#!/usr/bin/env python3
"""Script to fix config tests by applying json_output parameter removal pattern."""

import re

def fix_config_tests():
    file_path = "tests/unit/test_config_commands.py"
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Add SimpleNamespace import if not present
    if "from types import SimpleNamespace" not in content:
        content = content.replace(
            "from unittest.mock import AsyncMock, Mock, patch",
            "from types import SimpleNamespace\nfrom unittest.mock import AsyncMock, Mock, patch"
        )
    
    # Fix mock_context fixtures - replace Mock objects with SimpleNamespace
    fixture_pattern = r'(ctx\.obj = Mock\(\)[^}]+ctx\.obj\.profile = "default"[^}]*return ctx)'
    fixture_replacement = '''ctx.obj = SimpleNamespace(
            profile="default",
            verbose=False,
            json_output=False
        )
        return ctx'''
    
    content = re.sub(fixture_pattern, fixture_replacement, content, flags=re.MULTILINE | re.DOTALL)
    
    # Fix function calls - remove json_output parameters and add context setting
    patterns_to_fix = [
        (r'(await clear_config\([^,]+), json_output=(\w+)\)', r'mock_ctx.obj.json_output = \2\n        \1)'),
    ]
    
    for pattern, replacement in patterns_to_fix:
        content = re.sub(pattern, replacement, content)
    
    # Also fix any direct call patterns
    content = re.sub(
        r'await clear_config\(([^,]+), force=(\w+), json_output=(\w+)\)',
        r'mock_ctx.obj.json_output = \3\n        await clear_config(\1, force=\2)',
        content
    )
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("Config tests fixed!")

if __name__ == "__main__":
    fix_config_tests()