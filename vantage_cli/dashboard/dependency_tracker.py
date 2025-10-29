#!/usr/bin/env python3
"""Dependency Tracking Data Structure for Workers.

This module implements a dependency tracking system that manages workers
with dependencies, ensuring proper execution order and state management.
"""

import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set


class WorkerState(Enum):
    """Enum for worker states."""

    INIT = "init"
    READY = "ready"
    IN_PROGRESS = "in-progress"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class Worker:
    """Worker class with dependency tracking."""

    id: str
    worker_func: Callable
    state: WorkerState = WorkerState.INIT
    depends_on: Optional[List[str]] = field(default_factory=list)
    result: Optional[Any] = None
    error: Optional[str] = None

    def __post_init__(self):
        """Convert depends_on to empty list if None."""
        if self.depends_on is None:
            self.depends_on = []

    def can_start(self, completed_workers: Set[str]) -> bool:
        """Check if this worker can start based on dependencies."""
        if self.state != WorkerState.INIT:
            return False

        # Check if all dependencies are completed
        if self.depends_on:
            for dep in self.depends_on:
                if dep not in completed_workers:
                    return False

        return True

    def mark_ready(self):
        """Mark worker as ready to run."""
        self.state = WorkerState.READY

    def mark_in_progress(self):
        """Mark worker as in progress."""
        self.state = WorkerState.IN_PROGRESS

    def mark_complete(self, result: Any = None):
        """Mark worker as complete."""
        self.state = WorkerState.COMPLETE
        self.result = result

    def mark_failed(self, error: str):
        """Mark worker as failed."""
        self.state = WorkerState.FAILED
        self.error = error


class DependencyTracker:
    """Manages workers with dependencies and execution order."""

    def __init__(self, workers: List[Worker]):
        self.workers: Dict[str, Worker] = {w.id: w for w in workers}
        self.completed_workers: Set[str] = set()
        self.failed_workers: Set[str] = set()
        self.validate_dependencies()

    def validate_dependencies(self):
        """Validate that all dependencies exist and there are no cycles."""
        import logging

        logger = logging.getLogger(__name__)

        # Check that all dependencies exist and remove invalid ones
        for worker in self.workers.values():
            if worker.depends_on:
                valid_deps = []
                for dep in worker.depends_on:
                    if dep not in self.workers:
                        logger.warning(
                            f"Worker '{worker.id}' depends on non-existent worker '{dep}'. "
                            f"This dependency will be ignored. Available workers: {list(self.workers.keys())}"
                        )
                    else:
                        valid_deps.append(dep)
                # Update worker with only valid dependencies
                worker.depends_on = valid_deps

        # Check for circular dependencies using DFS
        def has_cycle(worker_id: str, visited: Set[str], rec_stack: Set[str]) -> bool:
            if worker_id in rec_stack:
                return True
            if worker_id in visited:
                return False

            visited.add(worker_id)
            rec_stack.add(worker_id)

            worker_depends = self.workers[worker_id].depends_on
            if worker_depends:
                for dep in worker_depends:
                    if has_cycle(dep, visited, rec_stack):
                        return True

            rec_stack.remove(worker_id)
            return False

        visited = set()
        for worker_id in self.workers:
            if worker_id not in visited:
                if has_cycle(worker_id, visited, set()):
                    raise ValueError(
                        f"Circular dependency detected involving worker '{worker_id}'"
                    )

    def get_ready_workers(self) -> List[Worker]:
        """Get workers that are ready to run (dependencies satisfied)."""
        ready = []
        for worker in self.workers.values():
            if worker.can_start(self.completed_workers):
                worker.mark_ready()
                ready.append(worker)
        return ready

    def mark_worker_complete(self, worker_id: str, result: Any = None):
        """Mark a worker as complete and update tracking."""
        if worker_id in self.workers:
            self.workers[worker_id].mark_complete(result)
            self.completed_workers.add(worker_id)

    def mark_worker_failed(self, worker_id: str, error: str):
        """Mark a worker as failed and update tracking."""
        if worker_id in self.workers:
            self.workers[worker_id].mark_failed(error)
            self.failed_workers.add(worker_id)

    def get_execution_order(self) -> List[List[str]]:
        """Get the execution order as layers (workers that can run in parallel)."""
        layers = []
        remaining = set(self.workers.keys())
        completed = set()

        while remaining:
            # Find workers that can run now
            current_layer = []
            for worker_id in remaining.copy():
                worker = self.workers[worker_id]
                if worker.depends_on is None or all(dep in completed for dep in worker.depends_on):
                    current_layer.append(worker_id)
                    remaining.remove(worker_id)

            if not current_layer:
                # No progress possible - circular dependency or other issue
                raise ValueError(f"Cannot resolve dependencies for remaining workers: {remaining}")

            layers.append(current_layer)
            completed.update(current_layer)

        return layers

    def get_status_summary(self) -> Dict[str, int]:
        """Get a summary of worker states."""
        summary = {state.value: 0 for state in WorkerState}
        for worker in self.workers.values():
            summary[worker.state.value] += 1
        return summary

    def is_complete(self) -> bool:
        """Check if all workers are complete."""
        return len(self.completed_workers) == len(self.workers)

    def has_failures(self) -> bool:
        """Check if any workers have failed."""
        return len(self.failed_workers) > 0

    def get_failed_workers(self) -> List[Worker]:
        """Get list of failed workers."""
        return [w for w in self.workers.values() if w.state == WorkerState.FAILED]

    def get_blocked_workers(self) -> List[Worker]:
        """Get workers that are blocked by failed dependencies."""
        blocked = []
        for worker in self.workers.values():
            if worker.state == WorkerState.INIT:
                # Check if any dependency failed
                if worker.depends_on:
                    for dep in worker.depends_on:
                        if dep in self.failed_workers:
                            blocked.append(worker)
                            break
        return blocked


# Example worker functions for testing
def install_cert_manager_worker(worker_id: str) -> Dict[str, Any]:
    """Simulate cert-manager installation."""
    time.sleep(random.uniform(1, 3))
    return {
        "worker_id": worker_id,
        "status": "success",
        "message": "cert-manager installed successfully",
        "version": "v1.12.0",
    }


def install_prometheus_worker(worker_id: str) -> Dict[str, Any]:
    """Simulate prometheus installation."""
    time.sleep(random.uniform(2, 4))
    return {
        "worker_id": worker_id,
        "status": "success",
        "message": "prometheus installed successfully",
        "version": "v2.45.0",
    }


def install_slinky_worker(worker_id: str) -> Dict[str, Any]:
    """Simulate slinky installation (depends on cert-manager and prometheus)."""
    time.sleep(random.uniform(1.5, 3.5))
    return {
        "worker_id": worker_id,
        "status": "success",
        "message": "slinky installed successfully",
        "version": "v1.0.0",
    }


def install_slurm_worker(worker_id: str) -> Dict[str, Any]:
    """Simulate slurm installation (depends on slinky)."""
    time.sleep(random.uniform(3, 5))
    # Simulate occasional failure
    if random.random() < 0.2:  # 20% chance of failure
        raise Exception("Failed to configure slurm scheduler")

    return {
        "worker_id": worker_id,
        "status": "success",
        "message": "slurm installed successfully",
        "version": "23.11.4",
    }


def install_jupyterhub_worker(worker_id: str) -> Dict[str, Any]:
    """Simulate jupyterhub installation (depends on slurm)."""
    time.sleep(random.uniform(2, 4))
    return {
        "worker_id": worker_id,
        "status": "success",
        "message": "jupyterhub installed successfully",
        "version": "4.0.0",
    }


# Example usage and testing
if __name__ == "__main__":
    # Define workers with dependencies
    workers = [
        Worker("cert-manager", install_cert_manager_worker, WorkerState.INIT),
        Worker("prometheus", install_prometheus_worker, WorkerState.INIT),
        Worker("slinky", install_slinky_worker, WorkerState.INIT, ["cert-manager", "prometheus"]),
        Worker("slurm", install_slurm_worker, WorkerState.INIT, ["slinky"]),
        Worker("jupyterhub", install_jupyterhub_worker, WorkerState.INIT, ["slurm"]),
    ]

    # Create dependency tracker
    tracker = DependencyTracker(workers)

    print("🔍 Dependency Analysis:")
    print("=" * 50)

    # Show execution order
    try:
        layers = tracker.get_execution_order()
        print("Execution layers (parallel execution possible within each layer):")
        for i, layer in enumerate(layers, 1):
            print(f"  Layer {i}: {', '.join(layer)}")
    except ValueError as e:
        print(f"❌ Dependency error: {e}")
        exit(1)

    print(f"\nTotal workers: {len(tracker.workers)}")
    print(f"Status summary: {tracker.get_status_summary()}")

    print("\n📋 Worker Details:")
    for worker in tracker.workers.values():
        deps = f" (depends on: {', '.join(worker.depends_on)})" if worker.depends_on else ""
        print(f"  • {worker.id}: {worker.state.value}{deps}")

    print("\n✅ Dependency validation passed!")
    print("Ready for execution with async worker management.")
