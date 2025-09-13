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
#!/usr/bin/env python3
"""Unit tests for vantage_cli.time_loop module."""

from unittest.mock import MagicMock, patch

import pendulum
import pytest

from vantage_cli.exceptions import VantageCliError
from vantage_cli.time_loop import Tick, TimeLoop


class TestTick:
    """Test the Tick dataclass."""

    def test_tick_creation(self):
        """Test creating a Tick with all required fields."""
        elapsed = pendulum.duration(seconds=5)
        total_elapsed = pendulum.duration(seconds=30)

        tick = Tick(counter=10, elapsed=elapsed, total_elapsed=total_elapsed)

        assert tick.counter == 10
        assert tick.elapsed == elapsed
        assert tick.total_elapsed == total_elapsed

    def test_tick_dataclass_properties(self):
        """Test that Tick has proper dataclass properties."""
        elapsed = pendulum.duration(seconds=1)
        total_elapsed = pendulum.duration(seconds=10)

        tick1 = Tick(counter=1, elapsed=elapsed, total_elapsed=total_elapsed)
        tick2 = Tick(counter=1, elapsed=elapsed, total_elapsed=total_elapsed)
        tick3 = Tick(counter=2, elapsed=elapsed, total_elapsed=total_elapsed)

        # Test equality
        assert tick1 == tick2
        assert tick1 != tick3

        # Test string representation
        assert str(tick1)
        assert repr(tick1)


class TestTimeLoop:
    """Test the TimeLoop class."""

    def test_time_loop_creation_with_duration_object(self):
        """Test creating TimeLoop with pendulum Duration object."""
        duration = pendulum.duration(seconds=60)
        time_loop = TimeLoop(duration=duration)

        assert time_loop.duration == duration
        assert time_loop.message == "Processing"
        assert time_loop.color == "green"
        assert time_loop.advent is None
        assert time_loop.moment is None
        assert time_loop.last_moment is None
        assert time_loop.counter == 0
        assert time_loop.progress is None

    def test_time_loop_creation_with_integer_duration(self):
        """Test creating TimeLoop with integer duration in seconds."""
        time_loop = TimeLoop(duration=120)

        assert time_loop.duration == pendulum.duration(seconds=120)
        assert time_loop.message == "Processing"
        assert time_loop.color == "green"

    def test_time_loop_creation_with_custom_message_and_color(self):
        """Test creating TimeLoop with custom message and color."""
        time_loop = TimeLoop(duration=60, message="Custom Processing", color="blue")

        assert time_loop.duration == pendulum.duration(seconds=60)
        assert time_loop.message == "Custom Processing"
        assert time_loop.color == "blue"

    def test_time_loop_creation_with_zero_duration_raises_error(self):
        """Test that creating TimeLoop with zero duration raises VantageCliError."""
        with pytest.raises(VantageCliError):
            TimeLoop(duration=0)

    def test_time_loop_creation_with_negative_duration_raises_error(self):
        """Test that creating TimeLoop with negative duration raises VantageCliError."""
        with pytest.raises(VantageCliError):
            TimeLoop(duration=-10)

    def test_time_loop_iterator_protocol(self):
        """Test that TimeLoop implements iterator protocol."""
        time_loop = TimeLoop(duration=60)

        # Should have __iter__ and __next__ methods
        assert hasattr(time_loop, "__iter__")
        assert hasattr(time_loop, "__next__")

        # __iter__ should return self
        assert time_loop.__iter__() == time_loop

    @patch("vantage_cli.time_loop.Progress")
    @patch("vantage_cli.time_loop.pendulum.now")
    def test_time_loop_iter_initializes_progress(self, mock_now, mock_progress_cls):
        """Test that __iter__ initializes progress and timing."""
        mock_progress = MagicMock()
        mock_progress_cls.return_value = mock_progress
        mock_now.return_value = pendulum.parse("2025-01-01T12:00:00Z")

        time_loop = TimeLoop(duration=60, message="Test Message", color="red")

        # Call __iter__
        result = time_loop.__iter__()

        # Should return self
        assert result == time_loop

        # Should initialize progress
        mock_progress_cls.assert_called_once()
        mock_progress.add_task.assert_called_once_with("[red]Test Message...", total=60.0)
        mock_progress.start.assert_called_once()

        # Should set timing
        assert time_loop.advent == mock_now.return_value
        assert time_loop.moment == mock_now.return_value
        assert time_loop.last_moment == mock_now.return_value
        assert time_loop.progress == mock_progress

    @patch("vantage_cli.time_loop.Progress")
    @patch("vantage_cli.time_loop.pendulum.now")
    def test_time_loop_next_returns_tick(self, mock_now, mock_progress_cls):
        """Test that __next__ returns a Tick object."""
        mock_progress = MagicMock()
        mock_progress.task_ids = [1]
        mock_progress.finished = False
        mock_progress_cls.return_value = mock_progress

        # Mock pendulum.now to return different times for each call
        start_time = pendulum.parse("2025-01-01T12:00:00Z")
        next_time = pendulum.parse("2025-01-01T12:00:05Z")
        cleanup_time = pendulum.parse("2025-01-01T12:00:10Z")
        # __iter__ calls now() once: for advent, last_moment, and moment (all same)
        # __next__ calls now() once: for new moment
        # __del__ may call now() once during cleanup
        mock_now.side_effect = [start_time, next_time, cleanup_time]

        time_loop = TimeLoop(duration=60)

        # Initialize the time loop
        iter(time_loop)

        # Call __next__
        tick = next(time_loop)

        # Should return a Tick
        assert isinstance(tick, Tick)
        assert tick.counter == 1
        assert tick.elapsed.total_seconds() == 5.0
        assert tick.total_elapsed.total_seconds() == 5.0

    @patch("vantage_cli.time_loop.Progress")
    @patch("vantage_cli.time_loop.pendulum.now")
    def test_time_loop_next_advances_progress(self, mock_now, mock_progress_cls):
        """Test that __next__ advances the progress bar."""
        mock_progress = MagicMock()
        mock_progress.task_ids = [1, 2]
        mock_progress.finished = False
        mock_progress_cls.return_value = mock_progress

        start_time = pendulum.parse("2025-01-01T12:00:00Z")
        next_time = pendulum.parse("2025-01-01T12:00:03Z")
        cleanup_time = pendulum.parse("2025-01-01T12:00:06Z")
        # __iter__ calls now() once, __next__ calls now() once, __del__ may call now() once
        mock_now.side_effect = [start_time, next_time, cleanup_time]

        time_loop = TimeLoop(duration=60)
        iter(time_loop)
        next(time_loop)

        # Should advance progress for each task
        assert mock_progress.advance.call_count == 2
        mock_progress.advance.assert_any_call(1, 3.0)
        mock_progress.advance.assert_any_call(2, 3.0)

    @patch("vantage_cli.time_loop.Progress")
    @patch("vantage_cli.time_loop.pendulum.now")
    def test_time_loop_next_raises_stop_iteration_when_finished(self, mock_now, mock_progress_cls):
        """Test that __next__ raises StopIteration when progress is finished."""
        mock_progress = MagicMock()
        mock_progress.task_ids = [1]
        mock_progress.finished = True
        mock_progress_cls.return_value = mock_progress

        start_time = pendulum.parse("2025-01-01T12:00:00Z")
        mock_now.return_value = start_time

        time_loop = TimeLoop(duration=60)
        iter(time_loop)

        # Should raise StopIteration
        with pytest.raises(StopIteration):
            next(time_loop)

        # Should clear the progress
        mock_progress.stop.assert_called_once()

    def test_time_loop_next_without_iter_raises_error(self):
        """Test that calling __next__ without __iter__ raises VantageCliError."""
        time_loop = TimeLoop(duration=60)

        # Should raise VantageCliError because progress is None
        with pytest.raises(VantageCliError):
            next(time_loop)

    @patch("vantage_cli.time_loop.Progress")
    @patch("vantage_cli.time_loop.pendulum.now")
    def test_time_loop_clear_resets_state(self, mock_now, mock_progress_cls):
        """Test that clear() resets the TimeLoop state."""
        mock_progress = MagicMock()
        mock_progress_cls.return_value = mock_progress

        current_time = pendulum.parse("2025-01-01T12:00:00Z")
        mock_now.return_value = current_time

        time_loop = TimeLoop(duration=60)
        iter(time_loop)

        # Modify state
        time_loop.counter = 5

        # Clear
        time_loop.clear()

        # Should stop progress
        mock_progress.stop.assert_called_once()

        # Should reset state
        assert time_loop.counter == 0
        assert time_loop.progress is None
        assert time_loop.moment == current_time
        assert time_loop.last_moment == current_time

    @patch("vantage_cli.time_loop.Progress")
    @patch("vantage_cli.time_loop.pendulum.now")
    def test_time_loop_clear_handles_none_progress(self, mock_now, mock_progress_cls):
        """Test that clear() handles None progress gracefully."""
        current_time = pendulum.parse("2025-01-01T12:00:00Z")
        mock_now.return_value = current_time

        time_loop = TimeLoop(duration=60)
        # Don't initialize progress

        # Should not raise error
        time_loop.clear()

        # Should reset state
        assert time_loop.counter == 0
        assert time_loop.progress is None

    @patch("vantage_cli.time_loop.Progress")
    @patch("vantage_cli.time_loop.pendulum.now")
    def test_time_loop_multiple_iterations(self, mock_now, mock_progress_cls):
        """Test TimeLoop with multiple iterations."""
        mock_progress = MagicMock()
        mock_progress.task_ids = [1]
        mock_progress.finished = False
        mock_progress_cls.return_value = mock_progress

        times = [
            pendulum.parse("2025-01-01T12:00:00Z"),  # __iter__ call
            pendulum.parse("2025-01-01T12:00:01Z"),  # first __next__
            pendulum.parse("2025-01-01T12:00:03Z"),  # second __next__
            pendulum.parse("2025-01-01T12:00:06Z"),  # cleanup call
        ]
        mock_now.side_effect = times

        time_loop = TimeLoop(duration=60)

        # Initialize
        iter(time_loop)

        # First iteration
        tick1 = next(time_loop)
        assert tick1.counter == 1
        assert tick1.elapsed.total_seconds() == 1.0

        # Second iteration (mock_progress.finished still False)
        tick2 = next(time_loop)
        assert tick2.counter == 2
        assert tick2.elapsed.total_seconds() == 2.0
        assert tick2.total_elapsed.total_seconds() == 3.0
