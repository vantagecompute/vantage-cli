#!/usr/bin/env python3
"""Script to fix example command tests by removing console patches."""

import re

def fix_example_tests():
    file_path = "/home/bdx/allcode/github/vantagecompute/vantage-cli/tests/unit/test_example.py"
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Remove console patches from with statements
    # Pattern 1: with (patch(...console...) as mock_console, patch(...)) as ...:
    content = re.sub(
        r'with \(\s*patch\("vantage_cli\.commands\.example\.console"\) as mock_console,\s*patch\(',
        'with patch(',
        content
    )
    
    # Pattern 2: patch("vantage_cli.commands.example.console") as mock_console,
    content = re.sub(
        r',?\s*patch\("vantage_cli\.commands\.example\.console"\) as mock_console,?\s*',
        '',
        content
    )
    
    # Replace mock_console references with mock_ctx.obj.console
    content = re.sub(
        r'mock_console\.print',
        'mock_ctx.obj.console.print',
        content
    )
    
    # Fix remaining parentheses issues from removed patches
    content = re.sub(
        r'with \(\s*patch\(',
        'with patch(',
        content
    )
    
    # Fix hanging commas and closing parens
    content = re.sub(
        r',\s*\)\s*:',
        ':',
        content
    )
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("Fixed example tests")

if __name__ == "__main__":
    fix_example_tests()