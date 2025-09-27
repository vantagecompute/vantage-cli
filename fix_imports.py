#!/usr/bin/env python3
"""Script to fix import ordering by moving logger initialization after imports."""

import re
from pathlib import Path


def fix_file_imports(file_path: Path) -> bool:
    """Fix import ordering in a single file.
    
    Returns True if file was modified, False otherwise.
    """
    content = file_path.read_text()
    
    # Pattern to match logger initialization before imports
    # Looks for: logger = logging.getLogger(__name__) followed by imports
    pattern = r'(logger = logging\.getLogger\(__name__\))\n((?:from .+?\nimport .+?\n)+)'
    
    # Check if file has the pattern
    if not re.search(pattern, content):
        return False
    
    # Find all imports after logger declaration
    lines = content.split('\n')
    logger_line_idx = None
    import_start_idx = None
    import_end_idx = None
    
    for i, line in enumerate(lines):
        if line.strip() == 'logger = logging.getLogger(__name__)':
            logger_line_idx = i
        elif logger_line_idx is not None and import_start_idx is None:
            if line.strip() and (line.strip().startswith('from ') or line.strip().startswith('import ')):
                import_start_idx = i
        elif import_start_idx is not None and import_end_idx is None:
            if line.strip() and not line.strip().startswith('from ') and not line.strip().startswith('import ') and not line.strip().startswith(')'):
                import_end_idx = i - 1
                break
    
    if logger_line_idx is None or import_start_idx is None:
        return False
    
    if import_end_idx is None:
        import_end_idx = len(lines) - 1
    
    # Extract the imports
    imports = lines[import_start_idx:import_end_idx + 1]
    
    # Remove the imports from their current location
    new_lines = lines[:import_start_idx] + lines[import_end_idx + 1:]
    
    # Find where to insert them (after logger line, before it)
    # We want them before logger
    insert_idx = logger_line_idx
    
    # Insert imports before logger
    new_lines = new_lines[:insert_idx] + imports + [''] + new_lines[insert_idx:]
    
    new_content = '\n'.join(new_lines)
    
    # Write back
    file_path.write_text(new_content)
    print(f"Fixed: {file_path}")
    return True


def main():
    """Fix all Python files in vantage_cli directory."""
    vantage_cli_dir = Path('vantage_cli')
    
    if not vantage_cli_dir.exists():
        print("vantage_cli directory not found")
        return
    
    python_files = list(vantage_cli_dir.rglob('*.py'))
    fixed_count = 0
    
    for py_file in python_files:
        if '__pycache__' in str(py_file):
            continue
        
        try:
            if fix_file_imports(py_file):
                fixed_count += 1
        except Exception as e:
            print(f"Error processing {py_file}: {e}")
    
    print(f"\nFixed {fixed_count} files")


if __name__ == '__main__':
    main()
