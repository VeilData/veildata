import time
from typing import Optional

from .traversal import traverse_and_redact as traverse_and_redact


class Timer:
    """
    A simple timer context manager to measure execution time.
    """

    def __init__(self) -> None:
        self._start_time: Optional[float] = None
        self._end_time: Optional[float] = None

    def __enter__(self) -> "Timer":
        self.start()
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.stop()

    def start(self) -> None:
        """Start the timer."""
        self._start_time = time.perf_counter()
        self._end_time = None

    def stop(self) -> None:
        """Stop the timer."""
        if self._start_time is None:
            raise RuntimeError("Timer was not started")
        self._end_time = time.perf_counter()

    @property
    def elapsed(self) -> float:
        """Return the elapsed time in seconds."""
        if self._start_time is None:
            raise RuntimeError("Timer was not started")

        if self._end_time is None:
            return time.perf_counter() - self._start_time

        return self._end_time - self._start_time
