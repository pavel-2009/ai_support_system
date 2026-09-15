"""Circut breaker implementation for handling failures in external service calls."""

import functools
import threading
import time
from enum import Enum


class State(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitOpen(Exception):
    """Raised when the circuit is open and calls are not allowed."""
    pass


class Circuit:
    """Class representing a circuit breaker for external service calls."""

    def __init__(self, failure_threshold=5, recovery_timeout=30, success_threshold=2):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self._lock = threading.Lock()
        self.state = State.CLOSED

        self._failures = 0
        self._successes = 0
        self._opened_at = 0.0

    def allow(self) -> bool:
        """Check if calls are allowed based on the current state of the circuit."""
        with self._lock:
            if self.state == State.OPEN:
                if time.monotonic() - self._opened_at >= self.recovery_timeout:
                    self.state = State.HALF_OPEN
                    self._successes = 0
                    return True
                return False
            return True

    def on_success(self) -> None:
        """Handle a successful call to the external service."""
        with self._lock:
            if self.state is State.HALF_OPEN:
                self._successes += 1
                if self._successes >= self.success_threshold:
                    self.state = State.CLOSED
                    self._failures = 0

            else:
                self._failures = 0

    def on_failure(self) -> None:
        """Handle a failed call to the external service."""
        with self._lock:
            if self.state is State.HALF_OPEN:
                self._trip()
                return
            self._failures += 1
            if self._failures >= self.failure_threshold:
                self._trip()

    def _trip(self) -> None:
        """Trip the circuit to the OPEN state."""
        self.state = State.OPEN
        self._opened_at = time.monotonic()
        self._failures = 0


def circuit(
    circ: Circuit,
    counts_as_failure=(Exception,),
):
    """Apply circuit breaker logic to an async external-service call."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if not circ.allow():
                raise CircuitOpen("Circuit is open. Calls are not allowed.")

            try:
                result = await func(*args, **kwargs)
            except counts_as_failure:
                circ.on_failure()
                raise
            else:
                circ.on_success()
                return result

        return wrapper

    return decorator
