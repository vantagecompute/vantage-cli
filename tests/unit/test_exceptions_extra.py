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
