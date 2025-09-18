#!/usr/bin/env python3

import re

# Read the file
with open('tests/unit/test_profile_crud.py', 'r') as f:
    content = f.read()

# Replace all instances of SimpleNamespace(...) that don't already have console=
pattern = r'SimpleNamespace\(([^)]+)\)'

def replace_func(match):
    params = match.group(1)
    # Check if console= is already in the params
    if 'console=' in params:
        return match.group(0)  # Return unchanged
    else:
        # Add console=MockConsole()
        return f'SimpleNamespace({params}, console=MockConsole())'

content = re.sub(pattern, replace_func, content)

# Write back to file
with open('tests/unit/test_profile_crud.py', 'w') as f:
    f.write(content)

print("Updated test_profile_crud.py")