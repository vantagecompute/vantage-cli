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
"""Test to ensure all command functions are decorated with handle_abort."""

import ast
from pathlib import Path
from typing import Dict, List, Tuple

import pytest

from vantage_cli.exceptions import handle_abort


class CommandFunctionVisitor(ast.NodeVisitor):
    """AST visitor to find command functions in Python files."""

    def __init__(self):
        self.functions: List[
            Tuple[str, str, List[str], int]
        ] = []  # (name, file, decorators, line)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions and check if they look like command functions."""
        # Check if function has typer.Context parameter
        has_typer_context = False
        for arg in node.args.args:
            if arg.annotation:
                if isinstance(arg.annotation, ast.Attribute):
                    # Handle typer.Context
                    if (
                        isinstance(arg.annotation.value, ast.Name)
                        and arg.annotation.value.id == "typer"
                        and arg.annotation.attr == "Context"
                    ):
                        has_typer_context = True
                        break
                elif isinstance(arg.annotation, ast.Name):
                    # Handle imported Context
                    if arg.annotation.id == "Context":
                        has_typer_context = True
                        break

        if has_typer_context:
            # Extract decorator names
            decorators = []
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Name):
                    decorators.append(decorator.id)
                elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
                    decorators.append(decorator.func.id)
                elif isinstance(decorator, ast.Attribute):
                    # Handle cases like @app.command()
                    decorators.append(f"{decorator.value.id}.{decorator.attr}")

            self.functions.append((node.name, "", decorators, node.lineno))

        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definitions and check if they look like command functions."""
        # Check if function has typer.Context parameter
        has_typer_context = False
        for arg in node.args.args:
            if arg.annotation:
                if isinstance(arg.annotation, ast.Attribute):
                    # Handle typer.Context
                    if (
                        isinstance(arg.annotation.value, ast.Name)
                        and arg.annotation.value.id == "typer"
                        and arg.annotation.attr == "Context"
                    ):
                        has_typer_context = True
                        break
                elif isinstance(arg.annotation, ast.Name):
                    # Handle imported Context
                    if arg.annotation.id == "Context":
                        has_typer_context = True
                        break

        if has_typer_context:
            # Extract decorator names
            decorators = []
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Name):
                    decorators.append(decorator.id)
                elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
                    decorators.append(decorator.func.id)
                elif isinstance(decorator, ast.Attribute):
                    # Handle cases like @app.command()
                    decorators.append(f"{decorator.value.id}.{decorator.attr}")

            self.functions.append((node.name, "", decorators, node.lineno))

        self.generic_visit(node)


def find_command_functions() -> Dict[str, List[Tuple[str, List[str], int]]]:
    """Find all command functions in the codebase."""
    commands_dir = Path(__file__).parent.parent.parent / "vantage_cli" / "commands"
    main_file = Path(__file__).parent.parent.parent / "vantage_cli" / "main.py"

    functions_by_file = {}

    # Scan all Python files in the commands directory
    for py_file in commands_dir.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue

        try:
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            visitor = CommandFunctionVisitor()
            visitor.visit(tree)

            if visitor.functions:
                rel_path = str(py_file.relative_to(Path(__file__).parent.parent.parent))
                functions_by_file[rel_path] = [
                    (name, decorators, line) for name, _, decorators, line in visitor.functions
                ]
        except Exception as e:
            # Skip files that can't be parsed
            print(f"Warning: Could not parse {py_file}: {e}")
            continue

    # Also check main.py for command functions
    try:
        with open(main_file, "r", encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content)
        visitor = CommandFunctionVisitor()
        visitor.visit(tree)

        if visitor.functions:
            rel_path = str(main_file.relative_to(Path(__file__).parent.parent.parent))
            functions_by_file[rel_path] = [
                (name, decorators, line) for name, _, decorators, line in visitor.functions
            ]
    except Exception as e:
        print(f"Warning: Could not parse main.py: {e}")

    return functions_by_file


def is_decorated_with_handle_abort(decorators: List[str]) -> bool:
    """Check if function is decorated with handle_abort."""
    return "handle_abort" in decorators


def is_utility_function(func_name: str, file_path: str) -> bool:
    """Check if this is a utility function that doesn't need handle_abort."""
    utility_patterns = [
        "get_cluster_by_name",
        "get_cluster_client_secret",
        "deploy_app_to_cluster",
        "_",  # Private functions
        "render_",  # Rendering functions
        "generate_",  # Generator functions
        "validate_",  # Validation functions
        "extract_",  # Extraction functions
        "format_",  # Formatting functions
        "parse_",  # Parsing functions
    ]

    # Check if it's a utility function based on name patterns
    for pattern in utility_patterns:
        if func_name.startswith(pattern):
            return True

    # Check if it's in a utility/helper file
    utility_files = [
        "utils.py",
        "render.py",
        "format.py",
        "common.py",
        "helpers.py",
    ]

    for util_file in utility_files:
        if file_path.endswith(util_file):
            return True

    return False


class TestHandleAbortDecoratorCoverage:
    """Test that all command functions are decorated with handle_abort."""

    def test_all_command_functions_have_handle_abort_decorator(self):
        """Test that every command function is decorated with @handle_abort."""
        functions_by_file = find_command_functions()

        missing_decorators = []

        for file_path, functions in functions_by_file.items():
            for func_name, decorators, line_no in functions:
                # Skip utility functions
                if is_utility_function(func_name, file_path):
                    continue

                # Check if function has handle_abort decorator
                if not is_decorated_with_handle_abort(decorators):
                    missing_decorators.append(f"{file_path}:{line_no} - {func_name}()")

        if missing_decorators:
            error_msg = (
                "The following command functions are missing the @handle_abort decorator:\n"
                + "\n".join(f"  - {func}" for func in missing_decorators)
                + "\n\nAll command functions should be decorated with @handle_abort to ensure "
                "user-friendly error messages instead of tracebacks."
            )
            pytest.fail(error_msg)

    def test_handle_abort_decorator_exists_and_is_importable(self):
        """Test that the handle_abort decorator exists and can be imported."""
        # This should not raise any import errors
        assert callable(handle_abort)

        # Test that it can decorate a function
        @handle_abort
        def test_function():
            pass

        assert callable(test_function)

    def test_sample_command_functions_are_detected(self):
        """Test that our detection mechanism finds known command functions."""
        functions_by_file = find_command_functions()

        # Check that we found some functions (sanity check)
        assert len(functions_by_file) > 0, "No command functions were detected"

        # Check for some known command functions that should exist
        all_functions = []
        for file_path, functions in functions_by_file.items():
            for func_name, decorators, line_no in functions:
                all_functions.append((file_path, func_name))

        # Look for some expected command functions
        expected_functions = [
            "list_clusters",
            "login",
            "logout",
            "whoami",
            "list_apps",
        ]

        found_functions = [name for _, name in all_functions]

        for expected in expected_functions:
            assert expected in found_functions, f"Expected command function '{expected}' not found"

    def test_utility_function_detection_works(self):
        """Test that utility function detection works correctly."""
        # Test utility function patterns
        assert is_utility_function("get_cluster_by_name", "any/file.py")
        assert is_utility_function("_private_function", "any/file.py")
        assert is_utility_function("render_table", "any/file.py")
        assert is_utility_function("validate_input", "any/file.py")

        # Test utility file patterns
        assert is_utility_function("any_function", "commands/cluster/utils.py")
        assert is_utility_function("any_function", "commands/render.py")

        # Test non-utility functions
        assert not is_utility_function("create_cluster", "commands/cluster/create.py")
        assert not is_utility_function("list_clusters", "commands/cluster/list.py")
        assert not is_utility_function("login", "main.py")
