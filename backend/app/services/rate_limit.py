"""
GhostWatt - services/rate_limit.py
Minimal in-memory sliding-window limiter used to slow down password / OTP guessing.
(Single-process only - fine for the MVP; use Redis or a gateway limiter in production.)
"""
import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Optional


class SlidingWindowLimiter:
    def __init__(self, max_events: int, window_seconds: int):
        self.max_events = max_events
        self.window = window_seconds
        self._events: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, q: Deque[float], now: float) -> None:
        while q and now - q[0] > self.window:
            q.popleft()

    def retry_after(self, key: str, now: Optional[float] = None) -> int:
        """Seconds until the key may try again (0 if it is not blocked)."""
        now = time.time() if now is None else now
        with self._lock:
            q = self._events[key]
            self._prune(q, now)
            if len(q) < self.max_events:
                return 0
            return max(1, int(self.window - (now - q[0])) + 1)

    def record(self, key: str, now: Optional[float] = None) -> None:
        now = time.time() if now is None else now
        with self._lock:
            q = self._events[key]
            self._prune(q, now)
            q.append(now)

    def clear(self, key: str) -> None:
        with self._lock:
            self._events.pop(key, None)

    def reset_all(self) -> None:
        with self._lock:
            self._events.clear()
