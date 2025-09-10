#!/usr/bin/env python3
"""Script to fix federation tests by applying json_output parameter removal pattern."""

import re

def fix_federation_tests():
    file_path = "tests/unit/test_federation_commands.py"
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix mock_context fixtures
    fixture_pattern = r'(ctx\.obj = Mock\(\)\s+ctx\.obj\.settings = Mock\(\)\s+ctx\.obj\.profile = "default")'
    fixture_replacement = 'ctx.obj = SimpleNamespace(\n            profile="default",\n            verbose=False,\n            json_output=False\n        )'
    
    content = re.sub(fixture_pattern, fixture_replacement, content, flags=re.MULTILINE)
    
    # Fix function calls - remove json_output parameters
    patterns_to_fix = [
        (r'list_federations\(([^,]+), json_output=\w+\)', r'list_federations(\1)'),
        (r'create_federation\(([^,]+), ([^,]+), ([^,]+), json_output=\w+\)', r'create_federation(\1, \2, \3)'),
        (r'delete_federation\(([^,]+), ([^,]+), force=(\w+), json_output=\w+\)', r'delete_federation(\1, \2, force=\3)'),
        (r'get_federation\(([^,]+), ([^,]+), json_output=\w+\)', r'get_federation(\1, \2)'),
        (r'update_federation\(([^,]+), ([^,]+), json_output=\w+\)', r'update_federation(\1, \2)'),
    ]
    
    for pattern, replacement in patterns_to_fix:
        content = re.sub(pattern, replacement, content)
    
    # Add context setting before function calls
    json_output_patterns = [
        (r'(mock_get_json_output\.return_value = True)\s+# Run the command\s+import asyncio\s+(asyncio\.run\(list_federations\(mock_context\)\))', 
         r'\1\n        mock_context.obj.json_output = True\n        # Run the command\n        import asyncio\n        \2'),
        (r'(mock_get_json_output\.return_value = False)\s+mock_console = Mock\(\)\s+mock_console_class\.return_value = mock_console\s+# Run the command\s+import asyncio\s+(asyncio\.run\(list_federations\(mock_context\)\))',
         r'\1\n        mock_console = Mock()\n        mock_console_class.return_value = mock_console\n        mock_context.obj.json_output = False\n        # Run the command\n        import asyncio\n        \2'),
    ]
    
    for pattern, replacement in json_output_patterns:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("Federation tests fixed!")

if __name__ == "__main__":
    fix_federation_tests()