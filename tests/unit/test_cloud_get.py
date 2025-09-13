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
"""Tests for cloud get command."""

from unittest.mock import Mock, patch

import pytest
import typer

from vantage_cli.commands.cloud.get import get_command


class TestCloudGetCommand:
    """Test suite for cloud get command."""

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

    def test_get_command_table_output(self, mock_ctx):
        """Test get command with table output (default)."""
        with (
            patch(
                "vantage_cli.commands.cloud.get.should_use_json", return_value=False
            ) as mock_should_use_json,
            patch("vantage_cli.commands.cloud.get.render_cloud_operation_result") as mock_render,
        ):
            get_command(ctx=mock_ctx, name="aws-production")

            # Verify should_use_json was called
            mock_should_use_json.assert_called_once_with(mock_ctx)

            # Verify render_cloud_operation_result was called
            mock_render.assert_called_once()
            call_args = mock_render.call_args
            assert call_args.kwargs["operation"] == "Get Cloud Configuration"
            assert call_args.kwargs["success"] is True
            assert call_args.kwargs["cloud_name"] == "aws-production"
            assert call_args.kwargs["json_output"] is False

            # Verify cloud data structure
            details = call_args.kwargs["details"]
            assert details["name"] == "aws-production"
            assert details["provider"] == "aws"
            assert details["region"] == "us-west-2"
            assert details["status"] == "active"

    def test_get_command_json_output(self, mock_ctx_with_json):
        """Test get command with JSON output enabled."""
        with (
            patch("vantage_cli.commands.cloud.get.should_use_json", return_value=True),
            patch("vantage_cli.commands.cloud.get.print_json") as mock_print_json,
        ):
            get_command(ctx=mock_ctx_with_json, name="gcp-staging")

            # Verify JSON output was called
            mock_print_json.assert_called_once()

            # Verify the data structure passed to print_json
            call_args = mock_print_json.call_args
            data = call_args.kwargs["data"]

            # Check cloud data structure
            assert data["name"] == "gcp-staging"
            assert data["provider"] == "aws"  # Mock always returns aws
            assert data["region"] == "us-west-2"
            assert data["status"] == "active"
            assert "created_at" in data
            assert "last_used" in data
            assert "credentials_configured" in data
            assert "default_region" in data
            assert "available_regions" in data

    def test_get_command_cloud_data_completeness(self, mock_ctx_with_json):
        """Test that all expected fields are present in mock cloud data."""
        with (
            patch("vantage_cli.commands.cloud.get.should_use_json", return_value=True),
            patch("vantage_cli.commands.cloud.get.print_json") as mock_print_json,
        ):
            get_command(ctx=mock_ctx_with_json, name="test-cloud")

            data = mock_print_json.call_args.kwargs["data"]

            # Check that all expected fields are present
            expected_fields = [
                "name",
                "provider",
                "region",
                "status",
                "created_at",
                "last_used",
                "credentials_configured",
                "default_region",
                "available_regions",
            ]
            for field in expected_fields:
                assert field in data, f"Field '{field}' missing from cloud data"

            # Verify field types and values
            assert isinstance(data["name"], str)
            assert isinstance(data["provider"], str)
            assert isinstance(data["region"], str)
            assert isinstance(data["status"], str)
            assert isinstance(data["credentials_configured"], bool)
            assert isinstance(data["available_regions"], list)
            assert len(data["available_regions"]) > 0

    def test_get_command_different_cloud_names(self, mock_ctx):
        """Test get command with different cloud names."""
        test_names = ["aws-prod", "gcp-dev", "azure-staging", "my-cloud-123"]

        with (
            patch("vantage_cli.commands.cloud.get.should_use_json", return_value=False),
            patch("vantage_cli.commands.cloud.get.render_cloud_operation_result") as mock_render,
        ):
            for name in test_names:
                get_command(ctx=mock_ctx, name=name)

                # Verify the name was passed correctly
                call_args = mock_render.call_args
                assert call_args.kwargs["cloud_name"] == name
                assert call_args.kwargs["details"]["name"] == name
                assert not call_args.kwargs["json_output"]

    def test_get_command_mock_data_structure(self, mock_ctx_with_json):
        """Test the structure and content of mock cloud data."""
        with (
            patch("vantage_cli.commands.cloud.get.should_use_json", return_value=True),
            patch("vantage_cli.commands.cloud.get.print_json") as mock_print_json,
        ):
            get_command(ctx=mock_ctx_with_json, name="test-structure")

            data = mock_print_json.call_args.kwargs["data"]

            # Verify specific mock data values
            assert data["provider"] == "aws"
            assert data["region"] == "us-west-2"
            assert data["status"] == "active"
            assert data["created_at"] == "2025-09-10T05:00:00Z"
            assert data["last_used"] == "2025-09-10T05:50:00Z"
            assert data["credentials_configured"] is True
            assert data["default_region"] == "us-west-2"
            assert "us-west-2" in data["available_regions"]
            assert "us-east-1" in data["available_regions"]
            assert "eu-west-1" in data["available_regions"]

    def test_get_command_message_format(self, mock_ctx):
        """Test that success message is properly formatted."""
        with (
            patch("vantage_cli.commands.cloud.get.should_use_json", return_value=False),
            patch("vantage_cli.commands.cloud.get.render_cloud_operation_result") as mock_render,
        ):
            cloud_name = "my-special-cloud"
            get_command(ctx=mock_ctx, name=cloud_name)

            call_args = mock_render.call_args

            # Verify the function was called with correct parameters
            assert call_args.kwargs["operation"] == "Get Cloud Configuration"
            assert call_args.kwargs["success"]
            assert call_args.kwargs["cloud_name"] == cloud_name
            assert not call_args.kwargs["json_output"]
            assert "name" in call_args.kwargs["details"]
            assert call_args.kwargs["details"]["name"] == cloud_name
