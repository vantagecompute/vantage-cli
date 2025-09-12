#!/usr/bin/env python3
"""Fix profile CRUD extra tests by removing json_output parameters and updating context setup."""

import re

def fix_profile_crud_extra_tests():
    # Read the file
    with open('tests/unit/test_profile_crud_extra.py', 'r') as f:
        content = f.read()
    
    # Add SimpleNamespace import
    content = re.sub(
        r'(from unittest.mock import MagicMock, patch)',
        r'from types import SimpleNamespace\nfrom unittest.mock import MagicMock, patch',
        content
    )
    
    # Pattern 1: Remove json_output=True/False from function calls
    content = re.sub(
        r'(create_profile\([^)]*), json_output=[^)]*\)',
        r'\1)',
        content
    )
    
    content = re.sub(
        r'(delete_profile\([^)]*), json_output=[^)]*\)',
        r'\1)',
        content
    )
    
    content = re.sub(
        r'(get_profile\([^)]*), json_output=[^)]*\)',
        r'\1)',
        content
    )
    
    content = re.sub(
        r'(list_profiles\([^)]*), json_output=[^)]*\)',
        r'\1)',
        content
    )
    
    content = re.sub(
        r'(use_profile\([^)]*), json_output=[^)]*\)',
        r'\1)',
        content
    )
    
    # Pattern 2: Handle multiline function calls with json_output
    content = re.sub(
        r'(create_profile\([\s\S]*?),\s*json_output=[^,)]*\s*\)',
        r'\1)',
        content
    )
    
    content = re.sub(
        r'(delete_profile\([\s\S]*?),\s*json_output=[^,)]*\s*\)',
        r'\1)',
        content
    )
    
    content = re.sub(
        r'(get_profile\([\s\S]*?),\s*json_output=[^,)]*\s*\)',
        r'\1)',
        content
    )
    
    content = re.sub(
        r'(list_profiles\([\s\S]*?),\s*json_output=[^,)]*\s*\)',
        r'\1)',
        content
    )
    
    content = re.sub(
        r'(use_profile\([\s\S]*?),\s*json_output=[^,)]*\s*\)',
        r'\1)',
        content
    )
    
    # Pattern 3: Update mock_ctx = MagicMock() to include SimpleNamespace setup
    def update_mock_ctx(match):
        method_content = match.group(0)
        # Check if SimpleNamespace is already set up
        if 'mock_ctx.obj = SimpleNamespace' in method_content:
            return method_content
        
        # Find the mock_ctx = MagicMock() line and add the obj setup after it
        method_content = re.sub(
            r'(mock_ctx = MagicMock\(\))',
            r'\1\n    mock_ctx.obj = SimpleNamespace(profile="default", verbose=False, json_output=True)',
            method_content
        )
        return method_content
    
    # Apply to all test functions
    content = re.sub(
        r'(def test_[^:]*:.*?)(?=def|\Z)',
        update_mock_ctx,
        content,
        flags=re.DOTALL
    )
    
    # Write the file back
    with open('tests/unit/test_profile_crud_extra.py', 'w') as f:
        f.write(content)
    
    print("Profile CRUD extra tests fixed!")

if __name__ == '__main__':
    fix_profile_crud_extra_tests()