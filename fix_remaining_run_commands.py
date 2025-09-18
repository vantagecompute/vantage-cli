#!/usr/bin/env python3
"""Fix remaining _run_command calls to include console parameter."""

import re

def fix_run_command_calls(file_path):
    """Fix _run_command calls that are missing console parameter."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Find all _run_command calls and fix them individually
    lines = content.split('\n')
    in_run_command = False
    run_command_lines = []
    run_command_start_idx = -1
    
    for i, line in enumerate(lines):
        if '_run_command(' in line and not in_run_command:
            in_run_command = True
            run_command_start_idx = i
            run_command_lines = [line]
        elif in_run_command:
            run_command_lines.append(line)
            if line.count(')') >= line.count('(') and ')' in line:
                # End of the _run_command call
                in_run_command = False
                
                # Check if this call needs console parameter
                full_call = '\n'.join(run_command_lines)
                if 'ctx.obj.console' not in full_call:
                    # Fix this call
                    if 'allow_fail=' in full_call:
                        # Insert console before allow_fail
                        pattern = r'(\s*)(allow_fail\s*=\s*(?:True|False))'
                        replacement = r'\1ctx.obj.console,\n\1\2'
                        fixed_call = re.sub(pattern, replacement, full_call)
                    else:
                        # Just add console before the closing parenthesis
                        # Find the last ) and insert console before it
                        lines_to_fix = full_call.split('\n')
                        for j in range(len(lines_to_fix)-1, -1, -1):
                            if ')' in lines_to_fix[j]:
                                # Insert console parameter
                                indent = len(lines_to_fix[j]) - len(lines_to_fix[j].lstrip())
                                if j == 0:
                                    # Single line call
                                    lines_to_fix[j] = lines_to_fix[j].replace(')', ', ctx.obj.console)')
                                else:
                                    # Multi-line call
                                    lines_to_fix[j] = lines_to_fix[j].replace(')', '')
                                    lines_to_fix.insert(j, ' ' * indent + 'ctx.obj.console')
                                    lines_to_fix.append(' ' * (indent - 4) + ')')
                                break
                        fixed_call = '\n'.join(lines_to_fix)
                    
                    # Replace the original lines
                    for j, fixed_line in enumerate(fixed_call.split('\n')):
                        if run_command_start_idx + j < len(lines):
                            lines[run_command_start_idx + j] = fixed_line
                        else:
                            lines.append(fixed_line)
                
                run_command_lines = []
                run_command_start_idx = -1
    
    new_content = '\n'.join(lines)
    
    # Check if changes were made
    if original_content != new_content:
        with open(file_path, 'w') as f:
            f.write(new_content)
        return True
    return False

# Fix the microk8s app file
microk8s_file = "/home/bdx/allcode/github/vantagecompute/vantage-cli/vantage_cli/apps/slurm_microk8s_localhost/app.py"
if fix_run_command_calls(microk8s_file):
    print("Fixed remaining _run_command calls in microk8s app")
else:
    print("No changes needed in microk8s app")