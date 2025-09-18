#!/usr/bin/env python3
"""
Fix unit tests to include console attribute in mock contexts.
"""

import os
import re
import subprocess
from pathlib import Path

# Find all test files that have console attribute errors
def find_failing_tests():
    """Run unit tests and extract files with console attribute errors."""
    try:
        result = subprocess.run(
            ["just", "unit"], 
            capture_output=True, 
            text=True, 
            cwd="/home/bdx/allcode/github/vantagecompute/vantage-cli"
        )
        
        # Extract test files with console attribute errors
        failing_tests = set()
        for line in result.stdout.split('\n'):
            if "'types.SimpleNamespace' object has no attribute 'console'" in line:
                # Extract test file from the line
                if "tests/unit/" in line:
                    test_file = re.search(r'tests/unit/[^:]+', line)
                    if test_file:
                        failing_tests.add(test_file.group())
        
        return list(failing_tests)
    except Exception as e:
        print(f"Error running tests: {e}")
        return []

def fix_mock_context_in_file(file_path):
    """Fix mock context creation in a specific file."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Pattern 1: SimpleNamespace objects without console
        pattern1 = r'SimpleNamespace\(([^)]*)\)'
        def add_console_to_simple_namespace(match):
            inner = match.group(1).strip()
            if 'console=' not in inner:
                if inner:
                    return f'SimpleNamespace({inner}, console=MockConsole())'
                else:
                    return 'SimpleNamespace(console=MockConsole())'
            return match.group(0)
        
        content = re.sub(pattern1, add_console_to_simple_namespace, content)
        
        # Pattern 2: ctx.obj assignments without console
        lines = content.split('\n')
        new_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Look for ctx.obj = SimpleNamespace(...) patterns
            if 'ctx.obj =' in line and 'SimpleNamespace' in line:
                # Check if console is already included
                if 'console=' not in line:
                    # Add console to the SimpleNamespace
                    if ')' in line:
                        line = line.replace(')', ', console=MockConsole())')
                    else:
                        line = line.replace('SimpleNamespace(', 'SimpleNamespace(console=MockConsole(), ')
            
            new_lines.append(line)
            i += 1
        
        new_content = '\n'.join(new_lines)
        
        # Add MockConsole import if needed and not present
        if 'MockConsole()' in new_content and 'from tests.conftest import MockConsole' not in new_content:
            # Find imports section and add MockConsole import
            import_pattern = r'(from tests\.conftest import [^)]*)'
            if re.search(import_pattern, new_content):
                new_content = re.sub(
                    import_pattern, 
                    r'\1, MockConsole', 
                    new_content
                )
            else:
                # Add new import after other test imports
                test_import_pattern = r'(import pytest[^\n]*\n)'
                if re.search(test_import_pattern, new_content):
                    new_content = re.sub(
                        test_import_pattern,
                        r'\1from tests.conftest import MockConsole\n',
                        new_content
                    )
        
        # Write back if changed
        if new_content != content:
            with open(file_path, 'w') as f:
                f.write(new_content)
            print(f"Fixed: {file_path}")
            return True
        else:
            print(f"No changes needed: {file_path}")
            return False
            
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

def main():
    """Main function to fix test files."""
    # For now, let's just fix files with obvious SimpleNamespace patterns
    test_dir = Path("/home/bdx/allcode/github/vantagecompute/vantage-cli/tests/unit")
    
    files_fixed = 0
    for test_file in test_dir.glob("*.py"):
        if fix_mock_context_in_file(test_file):
            files_fixed += 1
    
    print(f"Fixed {files_fixed} test files")

if __name__ == "__main__":
    main()