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
from vantage_cli.format import render_json, terminal_message


def test_terminal_message_basic(capsys):
    terminal_message("Hello World", subject="Greeting", color="blue", footer="Footer")
    out = capsys.readouterr().out
    assert "Greeting" in out
    assert "Hello World" in out
    assert "Footer" in out


def test_render_json_basic(capsys):
    render_json({"a": 1, "b": 2})
    out = capsys.readouterr().out
    assert '"a": 1' in out
    assert '"b": 2' in out
