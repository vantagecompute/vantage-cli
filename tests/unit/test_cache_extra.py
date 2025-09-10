import pytest

from vantage_cli.cache import (
    clear_token_cache,
    init_cache,
    load_tokens_from_cache,
    save_tokens_to_cache,
)
from vantage_cli.exceptions import Abort
from vantage_cli.schemas import TokenSet


def test_init_cache_permission_error(tmp_path, monkeypatch):
    """Simulate a non-writable cache dir by pointing the cache path at an existing file.

    Calling mkdir on that path will raise a FileExistsError which is caught and wrapped
    in an Abort by init_cache. This avoids trying to monkeypatch C-implemented Path methods.
    """
    # create a file path instead of directory
    bad_path = tmp_path / "cachefile"
    bad_path.write_text("x")
    monkeypatch.setattr("vantage_cli.cache.USER_TOKEN_CACHE_DIR", bad_path)

    from vantage_cli.cache import USER_TOKEN_CACHE_DIR as PATCHED_DIR  # local import after patch

    with pytest.raises(Abort) as exc:
        init_cache(PATCHED_DIR)
    # Message wording includes full sentence; verify key phrase
    assert "is not writable" in str(exc.value)


def test_load_tokens_missing_access(tmp_path, monkeypatch):
    # point cache dir to temp path
    profile_dir = tmp_path / "prof"
    profile_dir.mkdir(parents=True)
    monkeypatch.setattr("vantage_cli.cache.USER_TOKEN_CACHE_DIR", tmp_path)
    with pytest.raises(Abort):
        load_tokens_from_cache("prof")


def test_save_and_load_tokens_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr("vantage_cli.cache.USER_TOKEN_CACHE_DIR", tmp_path)
    ts = TokenSet(access_token="a.b.c", refresh_token="r.r.r")
    save_tokens_to_cache("p1", ts)
    loaded = load_tokens_from_cache("p1")
    assert loaded.access_token == "a.b.c"
    assert loaded.refresh_token == "r.r.r"


def test_clear_token_cache(tmp_path, monkeypatch):
    monkeypatch.setattr("vantage_cli.cache.USER_TOKEN_CACHE_DIR", tmp_path)
    ts = TokenSet(access_token="tok")
    save_tokens_to_cache("p2", ts)
    clear_token_cache("p2")
    # Clearing again should be idempotent
    clear_token_cache("p2")
    with pytest.raises(Abort):
        load_tokens_from_cache("p2")
