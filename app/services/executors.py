"""Reusable lifecycle wrapper for process-local worker pools."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor


class ManagedExecutor:
    """Lazily creates and safely recreates a bounded worker pool."""

    def __init__(self, max_workers: int, thread_name_prefix: str | None = None):
        self._max_workers = max_workers
        self._thread_name_prefix = thread_name_prefix
        self._executor: ThreadPoolExecutor | None = None
        self._lock = threading.Lock()

    def get(self) -> ThreadPoolExecutor:
        with self._lock:
            if self._executor is None or getattr(self._executor, "_shutdown", False):
                self._executor = ThreadPoolExecutor(
                    max_workers=self._max_workers,
                    thread_name_prefix=self._thread_name_prefix,
                )
            return self._executor

    def close(self) -> None:
        with self._lock:
            executor, self._executor = self._executor, None
        if executor is not None:
            # Cancel queued work and do not block application shutdown on an
            # active network/model task that cannot be interrupted safely.
            executor.shutdown(wait=False, cancel_futures=True)
