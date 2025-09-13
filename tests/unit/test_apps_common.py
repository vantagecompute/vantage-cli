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
from typing import Any, Dict

import pytest
import typer
from rich.console import Console

from vantage_cli.apps import common


@pytest.fixture()
def console() -> Console:
    return Console(record=True)


def test_validate_cluster_data_success(console: Console) -> None:
    data: Dict[str, Any] = {"clientId": "cid"}
    assert common.validate_cluster_data(data, console) is data


def test_validate_cluster_data_missing(console: Console) -> None:
    with pytest.raises(typer.Exit):
        common.validate_cluster_data(None, console)  # type: ignore[arg-type]


def test_validate_client_credentials_success(console: Console) -> None:
    data: Dict[str, Any] = {"clientId": "cid", "clientSecret": "shhh"}
    cid, secret = common.validate_client_credentials(data, console)
    assert cid == "cid"
    assert secret == "shhh"


def test_validate_client_credentials_missing_id(console: Console) -> None:
    with pytest.raises(typer.Exit):
        common.validate_client_credentials({}, console)


def test_require_client_secret_success(console: Console) -> None:
    assert common.require_client_secret("sek", console) == "sek"


def test_require_client_secret_missing(console: Console) -> None:
    with pytest.raises(typer.Exit):
        common.require_client_secret(None, console)
