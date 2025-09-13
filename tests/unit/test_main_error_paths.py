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
import datetime
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
import typer

from vantage_cli.exceptions import Abort
from vantage_cli.main import whoami
from vantage_cli.schemas import IdentityData, Persona, TokenSet


@pytest.mark.asyncio
async def test_whoami_success_rich_table():
    """Covers rich table rendering path (json_output False)."""
    with (
        patch("vantage_cli.main.extract_persona") as mock_extract,
        patch("vantage_cli.main.jwt.decode") as mock_decode,
        patch("vantage_cli.main.print_json") as mock_print_json,
        patch("vantage_cli.config.USER_CONFIG_FILE") as mock_config_file,
    ):
        ctx = Mock(spec=typer.Context)
        ctx.obj = SimpleNamespace(profile="test_profile", json_output=False)

        # Provide minimal settings mapping for required profile
        mock_config_file.read_text.return_value = json.dumps({"test_profile": {}})

        issued = int(datetime.datetime.now().timestamp()) - 100
        expires = int(datetime.datetime.now().timestamp()) + 100

        identity = IdentityData(email="user@example.com", client_id="client-123")
        persona = Persona(token_set=TokenSet(access_token="token123"), identity_data=identity)
        mock_extract.return_value = persona
        mock_decode.return_value = {
            "iat": issued,
            "exp": expires,
            "sub": "user-id-xyz",
            "name": "User Name",
        }

        await whoami(ctx)

        mock_print_json.assert_not_called()
        mock_extract.assert_called_once_with("test_profile")
        mock_decode.assert_called_once()


@pytest.mark.asyncio
async def test_whoami_error_json_output():
    """Covers error path with json_output True producing JSON error info."""
    with (
        patch("vantage_cli.main.extract_persona") as mock_extract,
        patch("vantage_cli.main.print_json") as mock_print_json,
        patch("vantage_cli.config.USER_CONFIG_FILE") as mock_config_file,
    ):
        ctx = Mock(spec=typer.Context)
        ctx.obj = SimpleNamespace(profile="p", json_output=True)
        mock_config_file.read_text.return_value = json.dumps({"p": {}})
        mock_extract.side_effect = Abort("boom")

        await whoami(ctx)

        mock_extract.assert_called_once_with("p")
        mock_print_json.assert_called_once()


@pytest.mark.asyncio
async def test_whoami_error_rich_panel():
    """Covers error path with json_output False producing rich Panel output."""
    with (
        patch("vantage_cli.main.extract_persona") as mock_extract,
        patch("vantage_cli.main.print_json") as mock_print_json,
        patch("vantage_cli.config.USER_CONFIG_FILE") as mock_config_file,
    ):
        ctx = Mock(spec=typer.Context)
        ctx.obj = SimpleNamespace(profile="err_prof", json_output=False)
        mock_config_file.read_text.return_value = json.dumps({"err_prof": {}})
        mock_extract.side_effect = Abort("nope")

        await whoami(ctx)

        mock_extract.assert_called_once_with("err_prof")
        mock_print_json.assert_not_called()
