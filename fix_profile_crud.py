#!/usr/bin/env python3
"""Fix profile CRUD tests by removing json_output parameters and updating context setup."""

import re

def fix_profile_crud_tests():
    # Read the file
    with open('tests/unit/test_profile_crud.py', 'r') as f:
        content = f.read()
    
    # Pattern 1: Remove json_output=True/False from function calls
    # create_profile(ctx=mock_ctx, profile_name="test_profile", json_output=True)
    content = re.sub(
        r'(create_profile\([^)]*), json_output=[^)]*\)',
        r'\1)',
        content
    )
    
    # delete_profile(ctx=mock_ctx, profile_name="nonexistent", json_output=False)
    content = re.sub(
        r'(delete_profile\([^)]*), json_output=[^)]*\)',
        r'\1)',
        content
    )
    
    # get_profile(ctx=mock_ctx, profile_name="test_profile", json_output=True)
    content = re.sub(
        r'(get_profile\([^)]*), json_output=[^)]*\)',
        r'\1)',
        content
    )
    
    # list_profiles(ctx=mock_ctx, json_output=True)
    content = re.sub(
        r'(list_profiles\([^)]*), json_output=[^)]*\)',
        r'\1)',
        content
    )
    
    # use_profile(ctx=mock_ctx, profile_name="test_profile", json_output=True)
    content = re.sub(
        r'(use_profile\([^)]*), json_output=[^)]*\)',
        r'\1)',
        content
    )
    
    # Pattern 2: Handle multiline function calls with json_output
    # For create_profile with multiple parameters including json_output
    content = re.sub(
        r'(create_profile\([\s\S]*?),\s*json_output=[^,)]*\s*\)',
        r'\1)',
        content
    )
    
    # Pattern 3: Update mock_ctx = MagicMock() to include SimpleNamespace setup
    # Look for test methods that don't already have the obj setup
    def update_mock_ctx(match):
        method_content = match.group(0)
        # Check if SimpleNamespace is already set up
        if 'mock_ctx.obj = SimpleNamespace' in method_content:
            return method_content
        
        # Find the mock_ctx = MagicMock() line and add the obj setup after it
        method_content = re.sub(
            r'(mock_ctx = MagicMock\(\))',
            r'\1\n        mock_ctx.obj = SimpleNamespace(profile="default", verbose=False, json_output=True)',
            method_content
        )
        return method_content
    
    # Apply to all test methods
    content = re.sub(
        r'(def test_[^:]*:.*?)(?=def|\Z)',
        update_mock_ctx,
        content,
        flags=re.DOTALL
    )
    
    # Write the file back
    with open('tests/unit/test_profile_crud.py', 'w') as f:
        f.write(content)
    
    print("Profile CRUD tests fixed!")

if __name__ == '__main__':
    fix_profile_crud_tests()