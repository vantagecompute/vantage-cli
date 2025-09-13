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
from pathlib import Path

import pytest
import typer

from vantage_cli import cache, exceptions
from vantage_cli.main import main as main_callback
from vantage_cli.schemas import TokenSet


@pytest.mark.asyncio
async def test_with_cache_async_success(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "USER_TOKEN_CACHE_DIR", tmp_path / "cdir")

    @cache.with_cache
    async def af():
        return "ok"

    result = await af()
    assert result == "ok"
    assert (cache.USER_TOKEN_CACHE_DIR / "token").is_dir()
    assert (cache.USER_TOKEN_CACHE_DIR / "info.txt").exists()


@pytest.mark.asyncio
async def test_with_cache_async_permission_error(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "USER_TOKEN_CACHE_DIR", tmp_path / "bad")
    original_mkdir = Path.mkdir

    def boom(self, *a, **kw):  # type: ignore
        raise PermissionError("no perms")

    monkeypatch.setattr(Path, "mkdir", boom)

    @cache.with_cache
    async def af():  # pragma: no cover - won't execute body
        return "nope"

    with pytest.raises(exceptions.Abort):
        await af()

    # restore for other tests
    monkeypatch.setattr(Path, "mkdir", original_mkdir)


def test_with_cache_sync_success(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "USER_TOKEN_CACHE_DIR", tmp_path / "cdir2")

    @cache.with_cache
    def fn():
        return 42

    assert fn() == 42
    assert (cache.USER_TOKEN_CACHE_DIR / "token").is_dir()
    assert (cache.USER_TOKEN_CACHE_DIR / "info.txt").exists()


def test_with_cache_sync_permission_error(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "USER_TOKEN_CACHE_DIR", tmp_path / "perm")
    original_mkdir = Path.mkdir

    def boom(self, *a, **kw):  # type: ignore
        raise OSError("disk full")

    monkeypatch.setattr(Path, "mkdir", boom)

    @cache.with_cache
    def fn():  # pragma: no cover - body skipped
        return 0

    with pytest.raises(exceptions.Abort):
        fn()

    monkeypatch.setattr(Path, "mkdir", original_mkdir)


def test_init_cache_success(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "USER_TOKEN_CACHE_DIR", tmp_path / "root")
    cache.init_cache(cache.USER_TOKEN_CACHE_DIR)
    assert (cache.USER_TOKEN_CACHE_DIR / "token").is_dir()
    assert (cache.USER_TOKEN_CACHE_DIR / "info.txt").read_text().startswith("This directory")


def test_load_tokens_access_only(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "USER_TOKEN_CACHE_DIR", tmp_path / "tokdir")
    prof = cache.USER_TOKEN_CACHE_DIR / "profA"
    prof.mkdir(parents=True)
    (prof / "access.token").write_text("acc")
    ts = cache.load_tokens_from_cache("profA")
    assert isinstance(ts, TokenSet)
    assert ts.access_token == "acc"
    assert ts.refresh_token is None


def test_main_callback_no_subcommand(monkeypatch, capsys):
    class DummyCtx:
        invoked_subcommand = None
        obj = None

        def get_help(self):
            return "Usage: vantage [OPTIONS] COMMAND [ARGS]...\n\nNo command provided. Use --help for help."

    dctx = DummyCtx()
    with pytest.raises(typer.Exit):
        main_callback(dctx)  # type: ignore[arg-type]
    out = capsys.readouterr().out
    assert "No command provided" in out
