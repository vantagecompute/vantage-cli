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
import pytest
from typer import Exit

from vantage_cli.exceptions import Abort, handle_abort


def test_handle_abort_sync(monkeypatch):
    @handle_abort
    def func():
        raise Abort("Failure happened", subject="Failed", log_message="boom")

    with pytest.raises(Exit):
        func()


def test_handle_abort_warn_only(monkeypatch):
    @handle_abort
    def func():
        raise Abort("Just a warn", subject="Warn", warn_only=True)

    # warn_only still results in exit because decorator always exits; ensure no error log crash
    with pytest.raises(Exit):
        func()
