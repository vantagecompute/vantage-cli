#!/usr/bin/env python3
"""Script to fix federation command tests to use ctx.obj.console instead of mocking Console class."""

import re

def fix_federation_tests():
    test_file = "/home/bdx/allcode/github/vantagecompute/vantage-cli/tests/unit/test_federation_commands.py"
    
    with open(test_file, 'r') as f:
        content = f.read()
    
    # Pattern to match the problematic test methods
    pattern = r'(@patch\("vantage_cli\.commands\.cluster\.federation\.\w+\.get_effective_json_output"\)\s+@patch\("vantage_cli\.commands\.cluster\.federation\.\w+\.Console"\)\s+def test_\w+\(\s+self, mock_console_class, mock_get_json_output, mock_context\s+\):.*?mock_console_class\.return_value = mock_console)'
    
    def replace_test_method(match):
        original = match.group(0)
        
        # Extract module name from the patch decorator
        module_match = re.search(r'@patch\("vantage_cli\.commands\.cluster\.federation\.(\w+)\.get_effective_json_output"\)', original)
        if not module_match:
            return original
        
        module_name = module_match.group(1)
        
        # Replace the decorators and method signature
        result = original.replace(
            f'@patch("vantage_cli.commands.cluster.federation.{module_name}.get_effective_json_output")\n    @patch("vantage_cli.commands.cluster.federation.{module_name}.Console")\n    def test_',
            f'@patch("vantage_cli.commands.cluster.federation.{module_name}.get_effective_json_output")\n    def test_'
        ).replace(
            'self, mock_console_class, mock_get_json_output, mock_context',
            'self, mock_get_json_output, mock_context'
        ).replace(
            'mock_console = Mock()\n        mock_console_class.return_value = mock_console',
            'from tests.conftest import MockConsole\n        mock_console = MockConsole()\n        mock_context.obj.console = mock_console'
        )
        
        return result
    
    # Apply the pattern replacement
    content = re.sub(pattern, replace_test_method, content, flags=re.DOTALL)
    
    # Also fix any remaining standalone Console patches that I might have missed
    content = re.sub(
        r'@patch\("vantage_cli\.commands\.cluster\.federation\.(\w+)\.Console"\)\s+@patch\("vantage_cli\.commands\.cluster\.federation\.(\w+)\.get_effective_json_output"\)',
        r'@patch("vantage_cli.commands.cluster.federation.\2.get_effective_json_output")',
        content
    )
    
    # Fix method signatures for reordered parameters  
    content = re.sub(
        r'def test_(\w+)\(\s+self, mock_console_class, mock_get_json_output',
        r'def test_\1(\n        self, mock_get_json_output',
        content
    )
    
    with open(test_file, 'w') as f:
        f.write(content)
    
    print("Federation tests fixed!")

if __name__ == "__main__":
    fix_federation_tests()