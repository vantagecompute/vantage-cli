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
"""Unit tests for vantage_cli.exceptions module."""

import pytest

from vantage_cli.exceptions import Abort


class TestAbortException:
    """Test the Abort exception class."""

    def test_abort_basic_creation(self):
        """Test basic Abort exception creation."""
        abort = Abort("Test message")
        assert str(abort) == "Test message"
        assert abort.subject is None
        assert abort.log_message is None

    def test_abort_with_subject(self):
        """Test Abort exception with subject."""
        abort = Abort("Test message", subject="Test Subject")
        assert str(abort) == "Test message"
        assert abort.subject == "Test Subject"
        assert abort.log_message is None

    def test_abort_with_log_message(self):
        """Test Abort exception with log message."""
        abort = Abort("Test message", log_message="Log this error")
        assert str(abort) == "Test message"
        assert abort.subject is None
        assert abort.log_message == "Log this error"

    def test_abort_with_all_parameters(self):
        """Test Abort exception with all parameters."""
        abort = Abort(
            "User message", subject="Error Subject", log_message="Internal error details"
        )
        assert str(abort) == "User message"
        assert abort.subject == "Error Subject"
        assert abort.log_message == "Internal error details"

    def test_abort_inheritance(self):
        """Test that Abort inherits from Exception."""
        abort = Abort("Test")
        assert isinstance(abort, Exception)

    def test_abort_can_be_raised(self):
        """Test that Abort can be raised and caught."""
        with pytest.raises(Abort) as exc_info:
            raise Abort("Test error", subject="Test Subject")

        assert str(exc_info.value) == "Test error"
        assert exc_info.value.subject == "Test Subject"
