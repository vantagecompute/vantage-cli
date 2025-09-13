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
"""Tests for cloud list command."""

from unittest.mock import Mock, patch

import pytest
import typer

from vantage_cli.commands.cloud.list import list_command


class TestCloudListCommand:
    """Test suite for cloud list command."""

    @pytest.fixture
    def mock_ctx(self):
        """Create a mock Typer context."""
        ctx = Mock(spec=typer.Context)
        ctx.obj = Mock()
        ctx.obj.json_output = False
        return ctx

    @pytest.fixture
    def mock_ctx_with_json(self):
        """Create a mock Typer context with JSON output enabled."""
        ctx = Mock(spec=typer.Context)
        ctx.obj = Mock()
        ctx.obj.json_output = True
        return ctx

    @pytest.fixture
    def mock_ctx_no_obj(self):
        """Create a mock Typer context with no obj."""
        ctx = Mock(spec=typer.Context)
        ctx.obj = None
        return ctx

    def test_list_command_table_output(self, mock_ctx):
        """Test list command with table output (default)."""
        with patch("vantage_cli.commands.cloud.list.render_clouds_table") as mock_render:
            list_command(ctx=mock_ctx)

            # Verify render_clouds_table was called with mock data
            mock_render.assert_called_once()
            clouds_data = mock_render.call_args[0][0]

            # Verify the structure of mock cloud data
            assert len(clouds_data) == 3
            assert clouds_data[0]["name"] == "aws-production"
            assert clouds_data[0]["provider"] == "aws"
            assert clouds_data[0]["region"] == "us-west-2"
            assert clouds_data[0]["status"] == "active"

            assert clouds_data[1]["name"] == "gcp-staging"
            assert clouds_data[1]["provider"] == "gcp"

            assert clouds_data[2]["name"] == "azure-dev"
            assert clouds_data[2]["provider"] == "azure"
            assert clouds_data[2]["status"] == "inactive"

    def test_list_command_json_output(self, mock_ctx_with_json):
        """Test list command with JSON output enabled."""
        with patch("rich.print_json") as mock_print_json:
            list_command(ctx=mock_ctx_with_json)

            # Verify JSON output was called
            mock_print_json.assert_called_once()

            # Verify the data structure passed to print_json
            call_args = mock_print_json.call_args
            data = call_args.kwargs["data"]
            assert "clouds" in data
            clouds = data["clouds"]
            assert len(clouds) == 3

            # Verify cloud data structure
            assert clouds[0]["name"] == "aws-production"
            assert clouds[1]["name"] == "gcp-staging"
            assert clouds[2]["name"] == "azure-dev"

    def test_list_command_no_ctx_obj(self, mock_ctx_no_obj):
        """Test list command when ctx.obj is None."""
        with patch("vantage_cli.commands.cloud.list.render_clouds_table") as mock_render:
            list_command(ctx=mock_ctx_no_obj)

            # Should default to table output when ctx.obj is None
            mock_render.assert_called_once()

    def test_list_command_ctx_obj_without_json_output(self):
        """Test list command when ctx.obj exists but has no json_output attribute."""
        ctx = Mock(spec=typer.Context)
        ctx.obj = Mock()
        # Don't set json_output attribute
        delattr(ctx.obj, "json_output") if hasattr(ctx.obj, "json_output") else None

        with patch("vantage_cli.commands.cloud.list.render_clouds_table") as mock_render:
            list_command(ctx=ctx)

            # Should default to table output when json_output attribute is missing
            mock_render.assert_called_once()

    def test_list_command_mock_data_completeness(self, mock_ctx_with_json):
        """Test that all expected fields are present in mock cloud data."""
        with patch("rich.print_json") as mock_print_json:
            list_command(ctx=mock_ctx_with_json)

            data = mock_print_json.call_args.kwargs["data"]
            clouds = data["clouds"]

            # Check that each cloud has all expected fields
            expected_fields = ["name", "provider", "region", "status", "created_at"]
            for cloud in clouds:
                for field in expected_fields:
                    assert field in cloud, f"Field '{field}' missing from cloud data"

                # Verify field types and values
                assert isinstance(cloud["name"], str)
                assert isinstance(cloud["provider"], str)
                assert isinstance(cloud["region"], str)
                assert cloud["status"] in ["active", "inactive"]
                assert cloud["created_at"].endswith("Z")  # ISO format check

    def test_list_command_provider_variety(self, mock_ctx_with_json):
        """Test that mock data includes different cloud providers."""
        with patch("rich.print_json") as mock_print_json:
            list_command(ctx=mock_ctx_with_json)

            data = mock_print_json.call_args.kwargs["data"]
            clouds = data["clouds"]

            providers = [cloud["provider"] for cloud in clouds]
            assert "aws" in providers
            assert "gcp" in providers
            assert "azure" in providers

            # Verify we have different statuses
            statuses = [cloud["status"] for cloud in clouds]
            assert "active" in statuses
            assert "inactive" in statuses
