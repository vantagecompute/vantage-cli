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
"""Tests for AsyncTyper functionality."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from vantage_cli import AsyncTyper


class TestAsyncTyper:
    """Test cases for AsyncTyper class."""

    def test_async_typer_initialization(self):
        """Test that AsyncTyper can be initialized properly."""
        app = AsyncTyper()
        assert isinstance(app, AsyncTyper)

    def test_maybe_run_async_with_async_function_no_loop(self):
        """Test maybe_run_async with async function when no event loop is running."""
        app = AsyncTyper()

        async def test_async_func():
            return "async_result"

        # This should use asyncio.run() since no loop is running
        result = app.maybe_run_async(test_async_func)
        assert result == "async_result"

    def test_maybe_run_async_with_async_function_existing_loop(self):
        """Test maybe_run_async with async function when event loop exists."""
        app = AsyncTyper()

        async def test_async_func():
            return "async_result"

        # Mock that we're already in an event loop
        with patch("asyncio.get_running_loop") as mock_get_loop:
            mock_get_loop.return_value = MagicMock()  # Simulate existing loop

            # This should return the coroutine directly
            result = app.maybe_run_async(test_async_func)
            assert asyncio.iscoroutine(result)

            # Clean up the coroutine
            result.close()

    def test_maybe_run_async_with_sync_function_returning_normal_value(self):
        """Test maybe_run_async with sync function returning normal value."""
        app = AsyncTyper()

        def test_sync_func():
            return "sync_result"

        result = app.maybe_run_async(test_sync_func)
        assert result == "sync_result"

    def test_maybe_run_async_with_sync_function_returning_coroutine_no_loop(self):
        """Test maybe_run_async with sync function that returns a coroutine, no loop."""
        app = AsyncTyper()

        async def inner_async():
            return "inner_async_result"

        def test_sync_func():
            return inner_async()

        # This should detect the returned coroutine and run it with asyncio.run()
        result = app.maybe_run_async(test_sync_func)
        assert result == "inner_async_result"

    def test_maybe_run_async_with_sync_function_returning_coroutine_existing_loop(self):
        """Test maybe_run_async with sync function that returns a coroutine, loop exists."""
        app = AsyncTyper()

        async def inner_async():
            return "inner_async_result"

        def test_sync_func():
            return inner_async()

        # Mock that we're already in an event loop
        with patch("asyncio.get_running_loop") as mock_get_loop:
            mock_get_loop.return_value = MagicMock()  # Simulate existing loop

            # This should return the coroutine directly
            result = app.maybe_run_async(test_sync_func)
            assert asyncio.iscoroutine(result)

            # Clean up the coroutine
            result.close()

    def test_maybe_run_async_with_args_and_kwargs(self):
        """Test maybe_run_async properly passes args and kwargs."""
        app = AsyncTyper()

        async def test_async_func(arg1, arg2, kwarg1=None, kwarg2=None):
            return f"{arg1}-{arg2}-{kwarg1}-{kwarg2}"

        result = app.maybe_run_async(test_async_func, "a", "b", kwarg1="c", kwarg2="d")
        assert result == "a-b-c-d"

    def test_maybe_run_async_sync_function_with_args_and_kwargs(self):
        """Test maybe_run_async with sync function with args and kwargs."""
        app = AsyncTyper()

        def test_sync_func(arg1, arg2, kwarg1=None, kwarg2=None):
            return f"{arg1}-{arg2}-{kwarg1}-{kwarg2}"

        result = app.maybe_run_async(test_sync_func, "a", "b", kwarg1="c", kwarg2="d")
        assert result == "a-b-c-d"

    def test_command_decorator_creates_sync_wrapper_for_async(self):
        """Test that the command decorator creates a sync wrapper for async functions."""
        app = AsyncTyper()

        @app.command()
        async def test_command():
            return "command_result"

        # The decorator should create a sync wrapper
        assert not asyncio.iscoroutinefunction(test_command)

    def test_command_decorator_preserves_sync_functions(self):
        """Test that the command decorator doesn't modify sync functions."""
        app = AsyncTyper()

        @app.command()
        def test_command():
            return "sync_command_result"

        # Should remain a regular sync function
        assert not asyncio.iscoroutinefunction(test_command)

    def test_callback_decorator_creates_sync_wrapper_for_async(self):
        """Test that the callback decorator creates a sync wrapper for async functions."""
        app = AsyncTyper()

        @app.callback()
        async def test_callback():
            return "callback_result"

        # The decorator should create a sync wrapper
        assert not asyncio.iscoroutinefunction(test_callback)

    def test_callback_decorator_preserves_sync_functions(self):
        """Test that the callback decorator doesn't modify sync functions."""
        app = AsyncTyper()

        @app.callback()
        def test_callback():
            return "sync_callback_result"

        # Should remain a regular sync function
        assert not asyncio.iscoroutinefunction(test_callback)

    @pytest.mark.asyncio
    async def test_maybe_run_async_in_existing_event_loop_context(self):
        """Test maybe_run_async when called from within an existing event loop."""
        app = AsyncTyper()

        async def test_async_func():
            return "async_in_loop_result"

        # This test runs in an event loop context, so should return coroutine
        result = app.maybe_run_async(test_async_func)
        assert asyncio.iscoroutine(result)

        # Actually await the result to test it works
        actual_result = await result
        assert actual_result == "async_in_loop_result"

    @pytest.mark.asyncio
    async def test_maybe_run_async_sync_func_returning_coroutine_in_loop(self):
        """Test maybe_run_async with sync func returning coroutine in event loop."""
        app = AsyncTyper()

        async def inner_async():
            return "inner_result"

        def test_sync_func():
            return inner_async()

        # This should return the coroutine since we're in a loop
        result = app.maybe_run_async(test_sync_func)
        assert asyncio.iscoroutine(result)

        # Actually await the result to test it works
        actual_result = await result
        assert actual_result == "inner_result"
