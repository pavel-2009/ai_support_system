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
