#!/usr/bin/env python3
"""Simple fix for all _run_command calls."""

import re

def fix_file():
    """Fix all _run_command calls in the microk8s app."""
    file_path = "/home/bdx/allcode/github/vantagecompute/vantage-cli/vantage_cli/apps/slurm_microk8s_localhost/app.py"
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Simple pattern: find ], allow_fail=True) and replace with ], ctx.obj.console, allow_fail=True)
    content = re.sub(r'],\s*allow_fail\s*=\s*(True|False)\s*\)', r'], ctx.obj.console, allow_fail=\1)', content)
    
    # Pattern for cases where there might be no allow_fail but still need console
    # Find _run_command calls that end with just ]) and don't have ctx.obj.console
    lines = content.split('\n')
    in_run_command = False
    modified_lines = []
    
    for line in lines:
        if '_run_command(' in line:
            in_run_command = True
            modified_lines.append(line)
        elif in_run_command and line.strip().endswith('])'):
            # This is the end of a _run_command call
            if 'ctx.obj.console' not in ''.join(modified_lines[-5:]):  # Check last few lines
                # Need to add console parameter
                modified_lines.append(line.replace('])', '], ctx.obj.console)'))
            else:
                modified_lines.append(line)
            in_run_command = False
        else:
            modified_lines.append(line)
    
    new_content = '\n'.join(modified_lines)
    
    with open(file_path, 'w') as f:
        f.write(new_content)
    
    print("Fixed all _run_command calls")

if __name__ == "__main__":
    fix_file()