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
"""Time-based loop utilities for the Vantage CLI."""

from __future__ import annotations

from dataclasses import dataclass

import pendulum
from rich.progress import Progress

from vantage_cli.exceptions import VantageCliError


@dataclass
class Tick:
    """Represents a single tick in a time loop with timing information."""

    counter: int
    elapsed: pendulum.Duration
    total_elapsed: pendulum.Duration


class TimeLoop:
    """Time-based loop with progress tracking and duration management."""

    advent: pendulum.DateTime | None
    moment: pendulum.DateTime | None
    last_moment: pendulum.DateTime | None
    counter: int
    progress: Progress | None
    duration: pendulum.Duration
    message: str
    color: str

    def __init__(
        self,
        duration: pendulum.Duration | int,
        message: str = "Processing",
        color: str = "green",
    ):
        self.advent = None
        self.moment = None
        self.last_moment = None
        self.counter = 0
        self.progress = None
        if isinstance(duration, int):
            VantageCliError.require_condition(
                duration > 0,
                "The duration must be a positive integer",
            )
            self.duration = pendulum.duration(seconds=duration)
        else:
            self.duration = duration
        self.message = message
        self.color = color

    def __del__(self):
        """Explicitly clear the progress meter if the time-loop is destroyed."""
        self.clear()

    def __iter__(self) -> "TimeLoop":
        """Start the iterator.

        Creates and starts the progress meter
        """
        now = pendulum.now()
        self.advent = now
        self.last_moment = now
        self.moment = now
        self.counter = 0
        self.progress = Progress()
        self.progress.add_task(
            f"[{self.color}]{self.message}...",
            total=self.duration.total_seconds(),
        )
        self.progress.start()
        return self

    def __next__(self) -> Tick:
        """Iterate the time loop and return a tick.

        If the duration is complete, clear the progress meter and stop iteration.
        """
        progress: Progress = VantageCliError.enforce_defined(
            self.progress,
            "Progress bar has not been initialized...this should not happen",
        )

        self.counter += 1
        self.last_moment = self.moment
        self.moment = pendulum.now()
        if self.moment is not None and self.last_moment is not None:
            elapsed: pendulum.Duration = self.moment - self.last_moment
        else:
            elapsed = pendulum.duration(seconds=0)
        if self.moment is not None and self.advent is not None:
            total_elapsed: pendulum.Duration = self.moment - self.advent
        else:
            total_elapsed = pendulum.duration(seconds=0)

        for task_id in progress.task_ids:
            progress.advance(task_id, elapsed.total_seconds())

        if progress.finished:
            self.clear()
            raise StopIteration

        return Tick(
            counter=self.counter,
            elapsed=elapsed,
            total_elapsed=total_elapsed,
        )

    def clear(self):
        """Clear the time-loop.

        Stops the progress meter (if set) and reset moments, counter, progress meter.
        """
        if self.progress is not None:
            self.progress.stop()
        self.counter = 0
        self.progress = None
        now = pendulum.now()
        self.moment = now
        self.last_moment = now
