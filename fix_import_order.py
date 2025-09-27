#!/usr/bin/env python3
"""Script to fix import ordering by moving logger after all imports."""

import re
import sys
from pathlib import Path


def fix_imports_in_file(filepath: Path) -> bool:
    """Fix import ordering in a Python file.
    
    Moves 'logger = logging.getLogger(__name__)' to after all imports.
    Returns True if file was modified.
    """
    try:
        content = filepath.read_text()
        lines = content.split('\n')
        
        # Find logger line
        logger_idx = None
        for i, line in enumerate(lines):
            if line.strip() == 'logger = logging.getLogger(__name__)':
                logger_idx = i
                break
        
        if logger_idx is None:
            return False
        
        # Check if there are imports after logger
        has_imports_after = False
        for i in range(logger_idx + 1, len(lines)):
            line = lines[i].strip()
            if line.startswith('from ') or line.startswith('import '):
                has_imports_after = True
                break
            # Stop if we hit a non-import, non-blank line
            if line and not line.startswith('#'):
                break
        
        if not has_imports_after:
            return False
        
        # Find all imports after logger (including multiline imports)
        imports_after_logger = []
        i = logger_idx + 1
        in_multiline = False
        
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Skip blank lines and comments immediately after logger
            if not stripped or stripped.startswith('#'):
                i += 1
                continue
            
            # Check if this is an import line
            if stripped.startswith('from ') or stripped.startswith('import '):
                imports_after_logger.append(i)
                # Check for multiline import
                if '(' in line and ')' not in line:
                    in_multiline = True
                i += 1
                continue
            
            # Handle multiline imports
            if in_multiline:
                imports_after_logger.append(i)
                if ')' in line:
                    in_multiline = False
                i += 1
                continue
            
            # Stop when we hit non-import code
            break
        
        if not imports_after_logger:
            return False
        
        # Extract import lines
        import_lines = [lines[idx] for idx in imports_after_logger]
        
        # Remove imports from their current positions (in reverse order)
        for idx in sorted(imports_after_logger, reverse=True):
            del lines[idx]
        
        # Find where to insert them (before logger, after other imports)
        # Find last import before logger
        insert_idx = logger_idx
        for i in range(logger_idx - 1, -1, -1):
            line = lines[i].strip()
            if line.startswith('from ') or line.startswith('import ') or line.endswith(')'):
                insert_idx = i + 1
                break
            if line and not line.startswith('#'):
                break
        
        # Insert imports before logger
        for import_line in reversed(import_lines):
            lines.insert(insert_idx, import_line)
        
        # Reconstruct content
        new_content = '\n'.join(lines)
        filepath.write_text(new_content)
        
        print(f"✓ Fixed: {filepath}")
        return True
        
    except Exception as e:
        print(f"✗ Error in {filepath}: {e}", file=sys.stderr)
        return False


def main():
    """Process all Python files in vantage_cli directory."""
    root = Path('vantage_cli')
    
    if not root.exists():
        print("Error: vantage_cli directory not found", file=sys.stderr)
        sys.exit(1)
    
    py_files = list(root.rglob('*.py'))
    py_files = [f for f in py_files if '__pycache__' not in str(f)]
    
    print(f"Found {len(py_files)} Python files")
    print("Fixing import ordering...\n")
    
    fixed_count = 0
    for py_file in py_files:
        if fix_imports_in_file(py_file):
            fixed_count += 1
    
    print(f"\n{'='*60}")
    print(f"Fixed {fixed_count} / {len(py_files)} files")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
