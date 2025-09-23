#!/usr/bin/env python3
# Copyright (C) 2025 Vantage Compute Corporation
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.
#!/usr/bin/env python3
"""
Combined CLI documentation generator.

This script combines command help extraction and documentation generation
into a single efficient process. It discovers all commands recursively,
extracts their help content, and generates comprehensive Markdown documentation
in one pass.
"""

import json
import re
import subprocess
import signal
import html
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from types import FrameType


class CombinedDocumentationGenerator:
    """Combined command help extractor and documentation generator."""
    
    def __init__(self, output_file: str, module_path: str):
        """Initialize the generator.
        
        Args:
            output_file: Output Markdown file path
            module_path: Python module path for the CLI
        """
        self.output_file = Path(output_file)
        self.module_path = module_path
        self.command_structure: Dict[str, Any] = {}
        self.timeout = 30  # seconds
        
    def run_command(self, cmd_args: List[str]) -> Tuple[str, int]:
        """Run a command and return output and exit code.
        
        Args:
            cmd_args: Command arguments list
            
        Returns:
            Tuple of (output, exit_code)
        """
        try:
            def timeout_handler(signum: int, frame: Optional[FrameType]) -> None:
                raise TimeoutError("Command timed out")
            
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(self.timeout)
            
            result = subprocess.run(
                cmd_args,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            signal.alarm(0)  # Cancel the alarm
            return result.stdout, result.returncode
            
        except subprocess.TimeoutExpired:
            return f"Command timed out: {' '.join(cmd_args)}", 1
        except TimeoutError:
            return f"Command timed out: {' '.join(cmd_args)}", 1
        except Exception as e:
            return f"Error running command: {e}", 1

    def run_command_with_env(self, cmd_args: List[str], env: dict) -> Tuple[str, int]:
        """Run a command with custom environment and return output and exit code.
        
        Args:
            cmd_args: Command arguments list
            env: Environment variables dictionary
            
        Returns:
            Tuple of (output, exit_code)
        """
        try:
            def timeout_handler(signum: int, frame: Optional[FrameType]) -> None:
                raise TimeoutError("Command timed out")
            
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(self.timeout)
            
            result = subprocess.run(
                cmd_args,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=env
            )
            
            signal.alarm(0)  # Cancel the alarm
            return result.stdout, result.returncode
            
        except subprocess.TimeoutExpired:
            return f"Command timed out: {' '.join(cmd_args)}", 1
        except TimeoutError:
            return f"Command timed out: {' '.join(cmd_args)}", 1
        except Exception as e:
            return f"Error running command: {e}", 1

    def discover_commands_recursive(self, command_path: Optional[List[str]] = None, max_depth: int = 2) -> Dict[str, Any]:
        """Recursively discover all commands and subcommands.
        
        Args:
            command_path: Current command path (None for root)
            max_depth: Maximum recursion depth to prevent infinite loops
            
        Returns:
            Nested dictionary of commands and subcommands
        """
        if command_path is None:
            command_path = []
        
        # Limit recursion depth to prevent excessive calls
        if len(command_path) >= max_depth:
            return {}
        
        print(f"Discovering commands at path: {' '.join(command_path) if command_path else 'root'}")
        
        # Get help for current path
        cmd_args = ["uv", "run", "python3", "-m", self.module_path] + command_path + ["--help"]
        
        # Set environment to disable colors
        import os
        env = os.environ.copy()
        env['NO_COLOR'] = '1'
        env['PY_COLORS'] = '0'
        
        help_output, code = self.run_command_with_env(cmd_args, env)
        
        # Strip ANSI escape sequences from the output
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        help_output = ansi_escape.sub('', help_output)
        
        if code != 0:
            print(f"Failed to get help for {' '.join(command_path)}: {help_output}")
            print(f"Command was: {' '.join(cmd_args)}")
            return {}
        
        # Parse commands from help output
        commands: Dict[str, Any] = {}
        in_commands_section = False
        
        print(f"Help output length: {len(help_output)}")
        print(f"First 200 chars: {repr(help_output[:200])}")
        
        for line in help_output.split('\n'):
            if '─ Commands ─' in line or 'Commands' in line:
                in_commands_section = True
                continue
            elif '╰─' in line and in_commands_section:
                in_commands_section = False
                break
            elif in_commands_section and line.strip():
                # Extract command name - it should be the first word after │ and before spaces/description
                # Format: │ command_name      Description text...
                match = re.match(r'│\s+(\w+)\s{2,}', line)
                if match:
                    cmd_name = match.group(1)
                    current_path = command_path + [cmd_name]
                    print(f"Found command: {' '.join(current_path)}")
                    
                    # Recursively discover subcommands
                    subcommands = self.discover_commands_recursive(current_path)
                    commands[cmd_name] = subcommands
        
        return commands

    def extract_command_help(self, command_path: List[str]) -> Optional[str]:
        """Extract help for a specific command path.
        
        Args:
            command_path: List of command parts (e.g., ['cluster', 'list'])
            
        Returns:
            Help output or None if failed
        """
        cmd_args = ["uv", "run", "python3", "-m", self.module_path] + command_path + ["--help"]
        cmd_str = " ".join(command_path)
        
        # Set environment to disable colors
        import os
        env = os.environ.copy()
        env['NO_COLOR'] = '1'
        env['PY_COLORS'] = '0'
        
        print(f"Extracting help for: {cmd_str}")
        output, code = self.run_command_with_env(cmd_args, env)
        
        # Strip ANSI escape sequences from the output
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        output = ansi_escape.sub('', output)
        
        if code == 0:
            return output
        else:
            print(f"Failed to get help for {cmd_str}: {output}")
            return None

    def extract_detailed_command_info(self, help_content: str) -> Dict[str, Any]:
        """Extract structured information from help content.
        
        Args:
            help_content: Raw help content
            
        Returns:
            Dictionary with usage, description, arguments, options
        """
        info: Dict[str, Any] = {
            "usage": "",
            "description": "",
            "arguments": [],
            "options": []
        }
        
        lines = help_content.split('\n')
        current_section = None
        
        for line in lines:
            line_stripped = line.strip()
            
            # Detect sections
            if line_stripped.startswith('Usage:'):
                current_section = 'usage'
                # Extract usage from the same line if present
                usage_match = re.match(r'Usage:\s*(.+)', line_stripped)
                if usage_match:
                    info["usage"] = usage_match.group(1).strip()
                continue
            elif '─ Arguments ─' in line:
                current_section = 'arguments'
                continue
            elif '─ Options ─' in line:
                current_section = 'options'
                continue
            elif line_stripped and not line.startswith(' ') and not line.startswith('│') and not line.startswith('╰'):
                if current_section is None:
                    # This might be description text
                    if info["description"]:
                        info["description"] += " " + line_stripped
                    else:
                        info["description"] = line_stripped
                continue
            
            # Parse content based on current section
            if current_section == 'usage' and line_stripped and not line.startswith('│'):
                if not info["usage"]:  # Only if we haven't captured it from Usage: line
                    info["usage"] = line_stripped
                    
            elif current_section == 'arguments' and line.startswith('│'):
                # Extract argument info
                arg_match = re.match(r'│\s+(\S+)\s+(.*)', line)
                if arg_match:
                    arg_name = arg_match.group(1)
                    arg_desc = arg_match.group(2).strip()
                    if arg_name and arg_name not in ['Arguments', '─', '╰']:
                        # Escape HTML-like tags in description
                        escaped_desc = self.escape_html_in_text(arg_desc)
                        info["arguments"].append(f"`{arg_name}` - {escaped_desc}")
                        
            elif current_section == 'options' and line.startswith('│'):
                # Extract option info
                # Pattern matches: │ --profile  -p      TEXT  Profile name to use [default: default]                │
                opt_match = re.match(r'│\s+(--?\w+(?:[\s-]+\w+)*)\s+(.*)', line)
                if opt_match:
                    opt_flags_raw = opt_match.group(1)
                    opt_desc = opt_match.group(2).strip()
                    if opt_flags_raw and opt_flags_raw not in ['Options', '─', '╰']:
                        # Clean up the flags - replace multiple spaces/dashes with proper format
                        # Convert "--profile  -p" to "--profile -p"
                        opt_flags = re.sub(r'\s+(-\w+)', r' \1', opt_flags_raw.strip())
                        # Escape HTML-like tags in description
                        escaped_desc = self.escape_html_in_text(opt_desc)
                        info["options"].append(f"`{opt_flags}` - {escaped_desc}")
        
        return info

    def clean_usage_line(self, usage: str) -> str:
        """Clean and format usage line.
        
        Args:
            usage: Raw usage string
            
        Returns:
            Cleaned usage string
        """
        if not usage:
            return ""
        
        # Replace python module calls with 'vantage'
        usage = re.sub(r'python3? -m vantage_cli\.main', 'vantage', usage)
        return usage.strip()

    def escape_html_in_text(self, text: str) -> str:
        """Escape HTML-like tags in text to prevent MDX parsing issues.
        
        Args:
            text: Text that may contain HTML-like content
            
        Returns:
            Text with HTML tags escaped
        """
        # Escape angle brackets that could be interpreted as HTML tags
        return html.escape(text, quote=False)

    def clean_and_escape_help_content(self, help_content: str) -> List[str]:
        """Clean and escape help content for safe display in CodeBlock.
        
        Args:
            help_content: Raw help content
            
        Returns:
            List of cleaned and escaped lines
        """
        lines = help_content.split('\n')
        cleaned_lines: List[str] = []
        for line in lines:
            # Replace python module calls with 'vantage'
            line = re.sub(r'python3? -m vantage_cli\.main', 'vantage', line)
            # Escape HTML tags to prevent MDX parsing issues
            line = self.escape_html_in_text(line)
            cleaned_lines.append(line)
        return cleaned_lines

    def generate_header(self) -> str:
        """Generate the documentation header.
        
        Returns:
            Markdown header content
        """
        return """# CLI Command Reference

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';
import CodeBlock from '@theme/CodeBlock';

This document provides a comprehensive reference for all available CLI commands and their options.

"""

    def generate_authentication_section(self) -> str:
        """Generate authentication commands section.
        
        Returns:
            Markdown content for authentication commands
        """
        markdown: List[str] = []
        markdown.append("## Authentication Commands\n")
        
        auth_commands = ["login", "logout", "whoami"]
        
        for cmd in auth_commands:
            if cmd in self.command_structure:
                help_content = self.extract_command_help([cmd])
                if help_content:
                    # Clean and escape the help content
                    cleaned_lines = self.clean_and_escape_help_content(help_content)
                    
                    # Show authentication commands directly (no tabs since they are top-level)
                    markdown.append(f"### {cmd.title()}\n")
                    markdown.append('<CodeBlock language="text" title="CLI Help">')
                    markdown.extend(cleaned_lines)
                    markdown.append("</CodeBlock>\n")
        
        return '\n'.join(markdown)

    def generate_command_section(self, command_name: str, command_data: Dict[str, Any]) -> str:
        """Generate documentation for a main command group.
        
        Args:
            command_name: Name of the command
            command_data: Nested command structure
            
        Returns:
            Markdown content for the command section
        """
        markdown: List[str] = []
        
        # Generate header by capitalizing command and appending " Management"
        if command_name == "version":
            header_title = "Version Information"
        else:
            header_title = f"{command_name.title()} Management"
        
        markdown.append(f"## {header_title}\n")
        
        # Generate subcommand sections using Docusaurus tabs
        if command_data:
            # Start tabs container
            markdown.append("<Tabs>")
            
            # First tab: main command help
            help_content = self.extract_command_help([command_name])
            if help_content:
                # Clean and escape the help content
                cleaned_lines = self.clean_and_escape_help_content(help_content)
                
                markdown.append(f"<TabItem value=\"{command_name}\" label=\"🔹 {command_name}\">")
                markdown.append("")
                markdown.append('<CodeBlock language="text" title="CLI Help">')
                markdown.extend(cleaned_lines)
                markdown.append("</CodeBlock>")
                markdown.append("")
                markdown.append("</TabItem>")
            
            # Subsequent tabs: subcommands
            for subcmd_name, subcmd_data in command_data.items():
                subcmd_path = [command_name, subcmd_name]
                tab_content = self.generate_subcommand_tab_content(subcmd_path, subcmd_data)
                if tab_content:
                    markdown.append(f"<TabItem value=\"{subcmd_name}\" label=\"{subcmd_name}\">")
                    markdown.append("")
                    markdown.append(tab_content)
                    markdown.append("")
                    markdown.append("</TabItem>")
            
            # End tabs container
            markdown.append("</Tabs>\n")
        else:
            # No subcommands, just show the main command help directly
            help_content = self.extract_command_help([command_name])
            if help_content:
                # Clean and escape the help content
                cleaned_lines = self.clean_and_escape_help_content(help_content)
                
                markdown.append('<CodeBlock language="text" title="CLI Help">')
                markdown.extend(cleaned_lines)
                markdown.append("</CodeBlock>\n")
        
        return '\n'.join(markdown)

    def generate_subcommand_tab_content(self, command_path: List[str], command_data: Dict[str, Any]) -> str:
        """Generate content for a subcommand tab.
        
        Args:
            command_path: Full command path (e.g., ['cluster', 'list'])
            command_data: Subcommand structure data
            
        Returns:
            Markdown content for the tab
        """
        markdown: List[str] = []
        
        help_content = self.extract_command_help(command_path)
        if not help_content:
            return ""
        
        # If this command has subcommands, show the main help and create nested tabs
        if command_data:
            # Add nested subcommands in nested tabs with main command first
            if len(command_data) > 0:
                markdown.append("<Tabs>")
                
                # First tab: main command help
                cleaned_lines = self.clean_and_escape_help_content(help_content)
                
                # Use just the last part of the command for the tab label - make it stand out
                main_command_label = command_path[-1]
                markdown.append(f"<TabItem value=\"{main_command_label}\" label=\"🔹 {main_command_label}\">")
                markdown.append("")
                markdown.append('<CodeBlock language="text" title="CLI Help">')
                markdown.extend(cleaned_lines)
                markdown.append("</CodeBlock>")
                markdown.append("")
                markdown.append("</TabItem>")
                
                # Subsequent tabs: nested subcommands
                for subcmd_name, subcmd_data in command_data.items():
                    nested_path = command_path + [subcmd_name]
                    nested_content = self.generate_subcommand_tab_content(nested_path, subcmd_data)
                    if nested_content:
                        markdown.append(f"<TabItem value=\"{subcmd_name}\" label=\"{subcmd_name}\">")
                        markdown.append("")
                        markdown.append(nested_content)
                        markdown.append("")
                        markdown.append("</TabItem>")
                
                markdown.append("</Tabs>")
        
        else:
            # Leaf command - show the entire help content in a code block
            cleaned_lines = self.clean_and_escape_help_content(help_content)
            
            markdown.append('<CodeBlock language="text" title="CLI Help">')
            markdown.extend(cleaned_lines)
            markdown.append("</CodeBlock>")
            markdown.append("")
        
        return '\n'.join(markdown)

    def generate_subcommand_section(self, command_path: List[str], command_data: Dict[str, Any], level: int = 3) -> str:
        """Generate documentation for a subcommand.
        
        Args:
            command_path: Full command path (e.g., ['cluster', 'federation'])
            command_data: Subcommand structure data
            level: Header level for Markdown
            
        Returns:
            Markdown content for the subcommand
        """
        # This method is now deprecated in favor of generate_subcommand_tab_content
        # but kept for backward compatibility
        return self.generate_subcommand_tab_content(command_path, command_data)

    def generate_full_documentation(self) -> str:
        """Generate the complete documentation content.
        
        Returns:
            Complete Markdown documentation
        """
        print("Starting command discovery...")
        
        # Discover all commands first
        self.command_structure = self.discover_commands_recursive()
        
        print(f"Discovered {len(self.command_structure)} top-level commands")
        
        # Start generating documentation
        markdown: List[str] = []
        markdown.append(self.generate_header())
        
        # Main CLI help
        print("Extracting main CLI help...")
        main_help = self.extract_command_help([])
        if main_help:
            # Extract, clean and escape the help output
            cleaned_lines = self.clean_and_escape_help_content(main_help)
            
            markdown.append('<CodeBlock language="text" title="CLI Help">')
            markdown.extend(cleaned_lines)
            markdown.append("</CodeBlock>\n")
        
        # Authentication commands
        print("Processing authentication commands...")
        markdown.append(self.generate_authentication_section())
        
        # Main command groups (generate all commands)
        skip_commands = {"login", "logout", "whoami", "config"}
        
        for command_name, command_data in self.command_structure.items():
            if command_name not in skip_commands:
                print(f"Processing command group: {command_name}")
                markdown.append(self.generate_command_section(command_name, command_data))
        
        # Configuration management (special case)
        if "config" in self.command_structure:
            print("Processing config commands...")
            markdown.append("## Configuration Management\n")
            config_data = self.command_structure["config"]
            
            # Add config commands in tabs with main command as first tab
            if config_data:
                markdown.append("<Tabs>")
                
                # First tab: main config command help
                config_help = self.extract_command_help(["config"])
                if config_help:
                    cleaned_lines = self.clean_and_escape_help_content(config_help)
                    
                    markdown.append("<TabItem value=\"config\" label=\"🔹 config\">")
                    markdown.append("")
                    markdown.append('<CodeBlock language="text" title="CLI Help">')
                    markdown.extend(cleaned_lines)
                    markdown.append("</CodeBlock>")
                    markdown.append("")
                    markdown.append("</TabItem>")
                
                # Subsequent tabs: config subcommands
                for subcmd_name, subcmd_data in config_data.items():
                    tab_content = self.generate_subcommand_tab_content(["config", subcmd_name], subcmd_data)
                    if tab_content:
                        markdown.append(f"<TabItem value=\"{subcmd_name}\" label=\"{subcmd_name}\">")
                        markdown.append("")
                        markdown.append(tab_content)
                        markdown.append("")
                        markdown.append("</TabItem>")
                
                markdown.append("</Tabs>\n")
            else:
                # No subcommands, just show main config help
                config_help = self.extract_command_help(["config"])
                if config_help:
                    cleaned_lines = self.clean_and_escape_help_content(config_help)
                    
                    markdown.append('<CodeBlock language="text" title="CLI Help">')
                    markdown.extend(cleaned_lines)
                    markdown.append("</CodeBlock>\n")
        
        return '\n'.join(markdown)

    def write_documentation(self, content: str):
        """Write the documentation to the output file.
        
        Args:
            content: Markdown content to write
        """
        # Ensure output directory exists
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.output_file, 'w') as f:
            f.write(content)
        
        print(f"Documentation written to: {self.output_file}")
        print(f"File size: {len(content)} characters")

    def generate(self):
        """Generate the complete documentation file."""
        print("Starting combined documentation generation...")
        print(f"Module path: {self.module_path}")
        print(f"Output file: {self.output_file}")
        
        try:
            content = self.generate_full_documentation()
            self.write_documentation(content)
            
            print(f"\nGeneration complete!")
            print(f"Commands documented: {len(self.command_structure)}")
            
        except Exception as e:
            print(f"Error generating documentation: {e}")
            raise


def main():
    """Main entry point."""
    import sys
    
    # Parse command line arguments
    output_file = "docusaurus/docs/commands.md"
    module_path = "vantage_cli.main"
    
    if len(sys.argv) > 1:
        output_file = sys.argv[1]
    if len(sys.argv) > 2:
        module_path = sys.argv[2]
    
    # Create generator and run
    generator = CombinedDocumentationGenerator(output_file, module_path)
    generator.generate()


if __name__ == "__main__":
    main()