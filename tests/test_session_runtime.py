import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from session_runtime import FairInputLock, SessionMetrics, atomic_json, EventJournal


class RuntimeTests(unittest.TestCase):
    def test_eight_clients_share_input_without_overlap_or_starvation(self):
        lock = FairInputLock()
        barrier = threading.Barrier(8)
        counts = [0] * 8
        failures = []
        active = []
        def worker(index):
            try:
                barrier.wait(timeout=3)
                for _ in range(30):
                    with lock:
                        self.assertEqual(active, [])
                        active.append(index)
                        with lock:  # nested screen capture under an atomic input action
                            counts[index] += 1
                            time.sleep(.0002)
                        active.pop()
            except Exception as exc:
                failures.append(exc)
        workers = [threading.Thread(target=worker, args=(i,), name=f"client-{i}", daemon=True) for i in range(8)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(5)
        self.assertFalse(any(w.is_alive() for w in workers))
        self.assertEqual(failures, [])
        self.assertEqual(counts, [30] * 8)
        self.assertEqual(lock.snapshot()["waiting"], 0)

    def test_waiters_acquire_in_arrival_order(self):
        lock = FairInputLock()
        order, threads = [], []
        lock.acquire()
        def worker(i):
            with lock:
                order.append(i)
        for i in range(8):
            thread = threading.Thread(target=worker, args=(i,), daemon=True)
            thread.start()
            threads.append(thread)
            deadline = time.monotonic() + 2
            while lock.snapshot()["waiting"] < i + 1 and time.monotonic() < deadline:
                time.sleep(.001)
        lock.release()
        for thread in threads:
            thread.join(2)
        self.assertEqual(order, list(range(8)))

    def test_timeout_does_not_block_later_waiters(self):
        lock = FairInputLock()
        lock.acquire()
        result = []
        worker = threading.Thread(target=lambda: result.append(lock.acquire(timeout=.02)), daemon=True)
        worker.start()
        worker.join(1)
        self.assertEqual(result, [False])
        self.assertEqual(lock.snapshot()["waiting"], 0)
        lock.release()
        self.assertTrue(lock.acquire(blocking=False))
        lock.release()

    def test_metrics_stop_clock_and_do_not_claim_catches(self):
        clock = [0]
        metrics = SessionMetrics(7, lambda: clock[0])
        clock[0] = 60
        metrics.finish()
        clock[0] = 120
        data = metrics.snapshot(games=10)
        self.assertEqual(data["rounds_per_hour"], 600)
        self.assertEqual(data["elapsed_seconds"], 60)
        self.assertNotIn("catches", data)

    def test_failed_profile_write_preserves_old_profile(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "profile.json"
            atomic_json(path, {"name": "İnel"})
            with self.assertRaises(ValueError):
                atomic_json(path, {"broken": float("nan")})
            self.assertEqual(json.loads(path.read_text()), {"name": "İnel"})
            self.assertEqual(len(list(Path(temp).iterdir())), 1)

    def test_journal_rotates_and_reports_write_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "session.jsonl"
            journal = EventJournal(path, max_bytes=1)
            journal.append("one")
            journal.append("two")
            self.assertTrue(path.with_suffix(".previous.jsonl").exists())
            self.assertEqual(json.loads(path.read_text())["message"], "two")
            bad = EventJournal(path / "not_a_directory")
            bad.append("three")
            self.assertIsNotNone(bad.error)
