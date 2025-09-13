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
from vantage_cli.schemas import TokenSet

# ---------------- cache.py additional error branch tests ----------------


def test_load_tokens_from_cache_missing_access(tmp_path, monkeypatch):
    # Point USER_TOKEN_CACHE_DIR to tmp
    monkeypatch.setattr(cache, "USER_TOKEN_CACHE_DIR", tmp_path)
    # Create profile dir but no access.token
    prof_dir = tmp_path / "prof"
    prof_dir.mkdir()
    refresh = prof_dir / "refresh.token"
    refresh.write_text("r1")
    with pytest.raises(exceptions.Abort) as ei:
        cache.load_tokens_from_cache("prof")
    assert "login" in str(ei.value).lower()


def test_save_tokens_to_cache_permission_error(monkeypatch, tmp_path):
    monkeypatch.setattr(cache, "USER_TOKEN_CACHE_DIR", tmp_path)
    # Make parent dir, then monkeypatch Path.write_text to raise for access token only
    token_set = TokenSet(access_token="a", refresh_token="b")

    original_write_text = Path.write_text

    def fail_once(self, *args, **kwargs):  # type: ignore
        if self.name == "access.token":
            raise PermissionError("nope")
        return original_write_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_once)
    # Expect Abort when saving
    with pytest.raises(PermissionError):  # underlying error bubbles (not wrapped in save)
        cache.save_tokens_to_cache("p", token_set)


@pytest.mark.parametrize("fail_on", ["access", "refresh"])
def test_clear_token_cache_handles_missing(monkeypatch, tmp_path, fail_on):
    monkeypatch.setattr(cache, "USER_TOKEN_CACHE_DIR", tmp_path)
    # Create both then delete one before calling clear
    prof_dir = tmp_path / "p"
    prof_dir.mkdir(parents=True)
    a = prof_dir / "access.token"
    r = prof_dir / "refresh.token"
    a.write_text("x")
    r.write_text("y")
    if fail_on == "access":
        a.unlink()
    else:
        r.unlink()
    # Should not raise
    cache.clear_token_cache("p")


# ---------------- exceptions.py decorator branches ----------------


def test_handle_abort_sync_warn_only(monkeypatch, capsys):
    @exceptions.handle_abort
    def f():
        raise exceptions.Abort("Warn message", subject="Warn", warn_only=True)

    # warn_only should still raise typer.Exit? The code exits unconditionally after printing.
    with pytest.raises(typer.Exit) as ei:
        f()
    assert ei.value.exit_code == 1
    out = capsys.readouterr().out
    assert "Warn message" in out
    # Because warn_only True, log_message (None) not logged; absence of "Original exception" text implicitly tested.


def test_handle_abort_sync_with_subject(monkeypatch, capsys):
    @exceptions.handle_abort
    def f():
        try:
            raise ValueError("orig")
        except ValueError:
            raise exceptions.Abort("Boom happened", subject="Fail", log_message="boom-log")

    with pytest.raises(typer.Exit) as ei:
        f()
    assert ei.value.exit_code == 1
    out = capsys.readouterr().out
    assert "Boom happened" in out and "Fail" in out


@pytest.mark.asyncio
async def test_handle_abort_async(monkeypatch, capsys):
    @exceptions.handle_abort
    async def af():
        raise exceptions.Abort("Async fail", subject="Async", log_message="async-log")

    with pytest.raises(typer.Exit):
        await af()
    out = capsys.readouterr().out
    assert "Async fail" in out and "Async" in out


@pytest.mark.asyncio
async def test_handle_abort_async_warn_only(monkeypatch, capsys):
    @exceptions.handle_abort
    async def af():
        raise exceptions.Abort("Async warn", subject="AsyncWarn", warn_only=True)

    with pytest.raises(typer.Exit):
        await af()
    out = capsys.readouterr().out
    assert "Async warn" in out and "AsyncWarn" in out


# Additional branches:
# 1. init_cache permission error raising Abort
# 2. decorator path with warn_only False but no log_message and no original_error (sync & async)


def test_init_cache_permission_error(monkeypatch, tmp_path):
    monkeypatch.setattr(cache, "USER_TOKEN_CACHE_DIR", tmp_path / "permfail")
    original_mkdir = Path.mkdir
    calls = {"n": 0}

    def fail_first(self, *a, **kw):  # type: ignore
        if calls["n"] == 0:
            calls["n"] += 1
            raise PermissionError("cannot make dir")
        return original_mkdir(self, *a, **kw)

    monkeypatch.setattr(Path, "mkdir", fail_first)
    with pytest.raises(exceptions.Abort) as ei:
        cache.init_cache(cache.USER_TOKEN_CACHE_DIR)
    msg = str(ei.value)
    assert "Cache directory" in msg and "is not writable" in msg and "cannot make dir" in msg


def test_handle_abort_sync_minimal(monkeypatch, capsys):
    @exceptions.handle_abort
    def f():
        raise exceptions.Abort("Minimal abort message")

    with pytest.raises(typer.Exit):
        f()
    out = capsys.readouterr().out
    assert "Minimal abort message" in out


@pytest.mark.asyncio
async def test_handle_abort_async_minimal(monkeypatch, capsys):
    @exceptions.handle_abort
    async def af():
        raise exceptions.Abort("Async minimal abort message")

    with pytest.raises(typer.Exit):
        await af()
    out = capsys.readouterr().out
    assert "Async minimal abort message" in out
