#!/usr/bin/env python3
"""
Script to fix _run_command calls in microk8s app to include console parameter.
"""

import re

def fix_run_command_calls():
    """Fix all _run_command calls to include console parameter."""
    file_path = "vantage_cli/apps/slurm_microk8s_localhost/app.py"
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Pattern to match _run_command calls that don't already have ctx.obj.console as first argument
    # This will match calls like:
    # _run_command([...])
    # _run_command([...], allow_fail=True)
    # But NOT calls that already have ctx.obj.console
    
    # First, let's handle simple single-line calls
    pattern1 = r'(\s+)_run_command\((\[[^\]]+\])\s*\)'
    replacement1 = r'\1_run_command(\2, ctx.obj.console)'
    content = re.sub(pattern1, replacement1, content)
    
    # Handle calls with allow_fail parameter
    pattern2 = r'(\s+)_run_command\((\[[^\]]+\]),\s*allow_fail=([^)]+)\)'
    replacement2 = r'\1_run_command(\2, ctx.obj.console, allow_fail=\3)'
    content = re.sub(pattern2, replacement2, content)
    
    # Handle multi-line _run_command calls - we need to be more careful here
    # Look for _run_command( followed by newlines and parameters
    lines = content.split('\n')
    new_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Check if this line starts a _run_command call
        if re.search(r'(\s+)_run_command\s*\($', line.strip()):
            # This is a multi-line _run_command call
            indent = re.match(r'(\s*)', line).group(1)
            new_lines.append(line)
            i += 1
            
            # Find the first parameter (should be a list)
            while i < len(lines) and not lines[i].strip().startswith('['):
                new_lines.append(lines[i])
                i += 1
            
            if i < len(lines) and lines[i].strip().startswith('['):
                # This line contains the command list - add console parameter after it
                cmd_line = lines[i]
                new_lines.append(cmd_line)
                i += 1
                
                # Insert console parameter
                console_line = f'{indent}    ctx.obj.console,'
                new_lines.append(console_line)
                
                # Continue with the rest of the call
                while i < len(lines):
                    new_lines.append(lines[i])
                    if ')' in lines[i]:
                        break
                    i += 1
                i += 1
            else:
                # Couldn't find the command list, just continue
                continue
        else:
            new_lines.append(line)
            i += 1
    
    content = '\n'.join(new_lines)
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print("Fixed _run_command calls in microk8s app")

if __name__ == "__main__":
    fix_run_command_calls()