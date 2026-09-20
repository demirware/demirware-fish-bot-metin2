"""Platform-independent scheduling, metrics and durable profile helpers."""
from collections import deque
from contextlib import contextmanager
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import tempfile
import threading
import time


class FairInputLock:
    """FIFO, reentrant lock shared by capture and input on one desktop.

    Reentrancy lets an atomic capture/input operation use the same capture
    helper as read-only detection. Never hold this lock during network I/O.
    """
    def __init__(self):
        self._condition = threading.Condition()
        self._queue = deque()
        self._owner = None
        self._depth = 0
        self._metrics = {}

    def acquire(self, blocking=True, timeout=-1):
        ident = threading.get_ident()
        started = time.monotonic()
        deadline = None if timeout < 0 else started + timeout
        with self._condition:
            if self._owner == ident:
                self._depth += 1
                return True
            if not blocking and (self._owner is not None or self._queue):
                return False
            ticket = object()
            self._queue.append(ticket)
            try:
                while self._owner is not None or self._queue[0] is not ticket:
                    remaining = None if deadline is None else deadline - time.monotonic()
                    if remaining is not None and remaining <= 0:
                        return False
                    self._condition.wait(remaining)
                self._queue.popleft()
                self._owner, self._depth = ident, 1
                self._held_since = time.monotonic()
                name = threading.current_thread().name
                self._active_name = name
                metric = self._metrics.setdefault(name, {"acquisitions": 0, "wait_seconds": 0.0,
                                                       "max_wait_seconds": 0.0, "held_seconds": 0.0})
                wait = self._held_since - started
                metric["acquisitions"] += 1
                metric["wait_seconds"] += wait
                metric["max_wait_seconds"] = max(metric["max_wait_seconds"], wait)
                return True
            finally:
                if ticket in self._queue:
                    self._queue.remove(ticket)
                    self._condition.notify_all()

    def release(self):
        with self._condition:
            if self._owner != threading.get_ident():
                raise RuntimeError("Input lock must be released by its owner")
            self._depth -= 1
            if not self._depth:
                self._metrics[self._active_name]["held_seconds"] += time.monotonic() - self._held_since
                self._owner = None
                self._condition.notify_all()

    def locked(self):
        with self._condition:
            return self._owner is not None

    def snapshot(self):
        with self._condition:
            return {"waiting": len(self._queue), "threads": {k: dict(v) for k, v in self._metrics.items()}}

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *args):
        self.release()


def atomic_json(path, data):
    """Replace only after a complete UTF-8 write; preserve old file on failure."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class SessionMetrics:
    def __init__(self, client_id, clock=time.monotonic):
        self._lock = threading.Lock()
        self._clock = clock
        self._started = self._progress = clock()
        self._ended = None
        self.client_id = client_id
        self.state = "Hazır"
        self.errors = 0
        self.recoveries = 0
        self.crates = 0
        self.message = ""

    def update(self, state=None, message=None, progress=False, error=False, recovery=False, crates=0):
        with self._lock:
            if state is not None:
                self.state = state
            if message is not None:
                self.message = str(message)[-600:]
            self.errors += int(error)
            self.recoveries += int(recovery)
            self.crates += crates
            if progress:
                self._progress = self._clock()

    def finish(self):
        with self._lock:
            self._ended = self._clock()

    def snapshot(self, games=0, bait=0):
        with self._lock:
            now = self._ended if self._ended is not None else self._clock()
            elapsed = max(0.0, now - self._started)
            return {"client": self.client_id + 1, "state": self.state, "rounds": games,
                    "bait_estimate": bait, "elapsed_seconds": round(elapsed, 1),
                    "rounds_per_hour": round(games * 3600 / elapsed, 1) if elapsed >= 1 else 0,
                    "idle_seconds": round(max(0, now - self._progress), 1),
                    "errors": self.errors, "recoveries": self.recoveries,
                    "crates": self.crates, "message": self.message}


class EventJournal:
    """One rotating local journal; a failed disk write must not crash workers."""
    def __init__(self, path, max_bytes=2_000_000):
        self.path = Path(path)
        self.max_bytes = max_bytes
        self._lock = threading.Lock()
        self.error = None

    def append(self, message):
        try:
            with self._lock:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                if self.path.exists() and self.path.stat().st_size > self.max_bytes:
                    os.replace(self.path, self.path.with_suffix(".previous.jsonl"))
                with self.path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps({"time": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                                        "message": str(message)}, ensure_ascii=False) + "\n")
                self.error = None
        except OSError as exc:
            self.error = str(exc)


DEFAULT_OPERATIONS = {
    "enabled": True,
    "start_spacing_seconds": 0.8,
    "session_minutes": 0,
    "poll_interval": 0.04,
    "minigame_timeout": 35,
    "max_detection_failures": 3,
    "max_recoveries": 2,
    "recovery_cooldown": 15,
    "jigsaw_every_rounds": 0,
    "jigsaw_max_seconds": 180,
    "workflows": {},
}
