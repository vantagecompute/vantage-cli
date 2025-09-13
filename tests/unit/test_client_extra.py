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
from unittest.mock import AsyncMock

import httpx
import pytest
from pydantic import BaseModel

from vantage_cli.client import make_oauth_request
from vantage_cli.exceptions import Abort


class DummyResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None


@pytest.mark.asyncio
async def test_make_oauth_request_success(monkeypatch):
    client = AsyncMock(spec=httpx.AsyncClient)

    class Resp:
        def raise_for_status(self):
            return None

        def json(self):  # sync like real httpx Response
            return {"access_token": "abc", "refresh_token": "def"}

    client.post.return_value = Resp()

    result = await make_oauth_request(client, "/token", {"k": "v"}, DummyResponse)
    assert result.access_token == "abc"
    assert result.refresh_token == "def"


@pytest.mark.asyncio
async def test_make_oauth_request_http_error(monkeypatch):
    client = AsyncMock(spec=httpx.AsyncClient)
    response = httpx.Response(400, request=httpx.Request("POST", "https://x/token"), json={"e": 1})
    http_error = httpx.HTTPStatusError("bad", request=response.request, response=response)

    async def raise_post(url_path, data):
        raise http_error

    client.post.side_effect = raise_post

    with pytest.raises(Abort):
        await make_oauth_request(client, "/token", {"k": "v"}, DummyResponse)


@pytest.mark.asyncio
async def test_make_oauth_request_request_error(monkeypatch):
    client = AsyncMock(spec=httpx.AsyncClient)
    client.post.side_effect = httpx.RequestError(
        "boom", request=httpx.Request("POST", "https://x/token")
    )
    with pytest.raises(Abort):
        await make_oauth_request(client, "/token", {"k": "v"}, DummyResponse)
