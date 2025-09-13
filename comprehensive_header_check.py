#!/usr/bin/env python3
"""
Comprehensive script to add Apache 2.0 license headers to all Python files 
that don't already have them.
"""

import os

# Apache License header template
APACHE_HEADER = '''# Copyright 2025 Vantage Compute, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
'''


def has_apache_header(content):
    """Check if file already has Apache license header."""
    return "Copyright 2025 Vantage Compute, Inc." in content


def add_header_to_file(filepath):
    """Add Apache header to a file that doesn't have it."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if has_apache_header(content):
            return False  # Already has header
        
        # Add header at the beginning of the file
        new_content = APACHE_HEADER + content
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"Added header to: {filepath}")
        return True
        
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False


def main():
    """Main function to add headers to all Python files."""
    project_root = "/home/bdx/allcode/github/vantagecompute/vantage-cli"
    
    # Directories to include
    include_dirs = [
        "vantage_cli",
        "tests", 
        "scripts"
    ]
    
    # Find all Python files in the specified directories
    python_files = []
    for include_dir in include_dirs:
        dir_path = os.path.join(project_root, include_dir)
        if os.path.exists(dir_path):
            for root, dirs, files in os.walk(dir_path):
                # Skip certain directories
                dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'node_modules', 'venv', '.venv']]
                
                for file in files:
                    if file.endswith('.py'):
                        python_files.append(os.path.join(root, file))
    
    print(f"Found {len(python_files)} Python files to check")
    
    updated_count = 0
    for filepath in python_files:
        if add_header_to_file(filepath):
            updated_count += 1
    
    print(f"\nCompleted: Added headers to {updated_count} files")
    
    # Verify completeness
    print("\nVerifying completeness...")
    missing_headers = []
    for filepath in python_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            if not has_apache_header(content):
                missing_headers.append(filepath)
        except Exception as e:
            print(f"Error checking {filepath}: {e}")
    
    if missing_headers:
        print(f"WARNING: {len(missing_headers)} files still missing headers:")
        for filepath in missing_headers:
            print(f"  - {filepath}")
    else:
        print("✅ All Python files now have Apache license headers!")


if __name__ == "__main__":
    main()