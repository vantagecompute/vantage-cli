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
"""Unit tests for vantage_cli.command_base module."""

from unittest.mock import MagicMock

from vantage_cli.command_base import (
    GlobalOptions,
    JsonOption,
    VerboseOption,
    get_effective_json_output,
    get_effective_verbose,
    get_global_options,
)


class TestTypeAnnotations:
    """Test the type annotations for command options."""

    def test_json_option_type(self):
        """Test JsonOption type annotation."""
        # JsonOption should be an Annotated type wrapping bool
        assert hasattr(JsonOption, "__origin__")
        # Check that it's based on bool
        assert JsonOption.__origin__ is bool

    def test_verbose_option_type(self):
        """Test VerboseOption type annotation."""
        # VerboseOption should be an Annotated type wrapping bool
        assert hasattr(VerboseOption, "__origin__")
        # Check that it's based on bool
        assert VerboseOption.__origin__ is bool


class TestGetEffectiveJsonOutput:
    """Test the get_effective_json_output utility function."""

    def test_local_json_true_overrides_global(self):
        """Test that local json=True takes precedence over global setting."""
        mock_ctx = MagicMock()
        mock_ctx.obj.json_output = False

        result = get_effective_json_output(mock_ctx, local_json=True)
        assert result is True

    def test_local_json_false_overrides_global(self):
        """Test that local json=False takes precedence over global setting."""
        mock_ctx = MagicMock()
        mock_ctx.obj.json_output = True

        result = get_effective_json_output(mock_ctx, local_json=False)
        assert result is True  # Global is True, local is False, should return global

    def test_falls_back_to_global_when_local_not_specified(self):
        """Test fallback to global setting when local is not specified."""
        mock_ctx = MagicMock()
        mock_ctx.obj.json_output = True

        # Local not specified (False is the default)
        result = get_effective_json_output(mock_ctx, local_json=False)
        assert result is True  # Should use global setting

    def test_global_json_true_when_local_false(self):
        """Test using global json=True when local is False (default)."""
        mock_ctx = MagicMock()
        mock_ctx.obj.json_output = True

        # When local is explicitly False but global is True, global wins
        result = get_effective_json_output(mock_ctx, local_json=False)
        assert result is True

    def test_no_global_context_defaults_to_local(self):
        """Test behavior when no global context is available."""
        mock_ctx = MagicMock()
        mock_ctx.obj = None

        result = get_effective_json_output(mock_ctx, local_json=True)
        assert result is True

    def test_no_global_json_attribute_defaults_to_local(self):
        """Test behavior when global context has no json_output attribute."""
        mock_ctx = MagicMock()
        mock_ctx.obj = MagicMock(spec=[])  # obj without json_output attribute

        result = get_effective_json_output(mock_ctx, local_json=True)
        assert result is True

    def test_getattr_fallback_behavior(self):
        """Test getattr fallback when json_output doesn't exist."""
        mock_ctx = MagicMock()
        # Mock obj exists but doesn't have json_output attribute
        del mock_ctx.obj.json_output

        result = get_effective_json_output(mock_ctx, local_json=True)
        assert result is True


class TestGetEffectiveVerbose:
    """Test the get_effective_verbose utility function."""

    def test_local_verbose_true_overrides_global(self):
        """Test that local verbose=True takes precedence over global setting."""
        mock_ctx = MagicMock()
        mock_ctx.obj.verbose = False

        result = get_effective_verbose(mock_ctx, local_verbose=True)
        assert result is True

    def test_local_verbose_false_overrides_global(self):
        """Test that local verbose=False takes precedence over global setting."""
        mock_ctx = MagicMock()
        mock_ctx.obj.verbose = True

        result = get_effective_verbose(mock_ctx, local_verbose=False)
        assert result is True  # Global is True, local is False, should return global

    def test_falls_back_to_global_verbose(self):
        """Test fallback to global verbose setting."""
        mock_ctx = MagicMock()
        mock_ctx.obj.verbose = True

        # Local not specified (False is the default)
        result = get_effective_verbose(mock_ctx, local_verbose=False)
        assert result is True  # Should use global setting

    def test_no_global_context_defaults_to_local_verbose(self):
        """Test behavior when no global context is available."""
        mock_ctx = MagicMock()
        mock_ctx.obj = None

        result = get_effective_verbose(mock_ctx, local_verbose=True)
        assert result is True

    def test_no_global_verbose_attribute_defaults_to_local(self):
        """Test behavior when global context has no verbose attribute."""
        mock_ctx = MagicMock()
        mock_ctx.obj = MagicMock(spec=[])  # obj without verbose attribute

        result = get_effective_verbose(mock_ctx, local_verbose=True)
        assert result is True


class TestGlobalOptions:
    """Test the GlobalOptions class."""

    def test_global_options_creation(self):
        """Test creating GlobalOptions instance."""
        mock_ctx = MagicMock()
        mock_ctx.obj = None

        options = GlobalOptions(mock_ctx)

        # Check default values
        assert options.verbose is False
        assert options.json_output is False

    def test_global_options_with_values(self):
        """Test creating GlobalOptions with specific values."""
        mock_ctx = MagicMock()
        mock_ctx.obj = None

        options = GlobalOptions(mock_ctx, local_json=True, local_verbose=True)

        assert options.verbose is True
        assert options.json_output is True

    def test_global_options_field_types(self):
        """Test that GlobalOptions fields have correct types."""
        mock_ctx = MagicMock()
        mock_ctx.obj = None

        options = GlobalOptions(mock_ctx)

        # These should be boolean fields
        assert isinstance(options.verbose, bool)
        assert isinstance(options.json_output, bool)

    def test_global_options_with_context_values(self):
        """Test GlobalOptions inheriting from context."""
        mock_ctx = MagicMock()
        mock_ctx.obj.verbose = True
        mock_ctx.obj.json_output = True
        mock_ctx.obj.profile = "test-profile"

        options = GlobalOptions(mock_ctx)

        assert options.verbose is True
        assert options.json_output is True
        assert options.profile == "test-profile"


class TestGlobalOptionsFactory:
    """Test the get_global_options factory function."""

    def test_factory_function(self):
        """Test creating GlobalOptions via factory function."""
        mock_ctx = MagicMock()
        mock_ctx.obj = None

        options = get_global_options(mock_ctx, json_output=True, verbose=True)

        assert options.verbose is True
        assert options.json_output is True
