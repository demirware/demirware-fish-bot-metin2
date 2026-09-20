"""Supervisor tests against a simulated fishing worker, with no game input."""
import importlib.util
from pathlib import Path
import sys
import threading
import types
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from session_runtime import FairInputLock


class SimulatedFishingBot:
    STOP_BAIT_DEPLETED = "bait_depleted"
    STOP_INVENTORY_FULL = "inventory_full"
    STOP_MANUAL = "manual"
    def __init__(self, config, reason="inventory_full", bait=200):
        self.config, self.reason = config, reason
        self.bot_id = 0
        self.bait_counter, self.bait_keys = bait, ["1"]
        self.total_games = 0
        self.running, self.paused = True, False
        self.human = Mock()
        self.window_manager = Mock()
        self.on_status_update = Mock()
        self.on_bait_update = Mock()
        self.on_bot_stop = Mock()
        self.stop_reason = None
        self._stop_notified = False
        self.sct = None
        self.mouse_backend = Mock()
    def start(self):
        self.total_games += 1
        self.stop_reason = self.reason
        self.running = False
        self._notify_bot_stop_once()
    def _stop_bot(self, reason, status=None):
        self.running = False
        self.stop_reason = reason
        self._notify_bot_stop_once()
    def _notify_bot_stop_once(self):
        if not self._stop_notified:
            self.on_bot_stop(self.bot_id)
            self._stop_notified = True
    def stop(self):
        self.running = False
        self.stop_reason = self.STOP_MANUAL


class ManagedSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fake_base = types.ModuleType("fishing_bot")
        fake_base.FishingBot = SimulatedFishingBot
        fake_utils = types.ModuleType("utils")
        fake_utils.input_lock = FairInputLock()
        fake_wm = types.ModuleType("window_manager")
        fake_wm.WindowActivationError = RuntimeError
        fake_mss = types.ModuleType("mss")
        fake_mss.mss = Mock()
        spec = importlib.util.spec_from_file_location("_managed_test", Path(__file__).resolve().parents[1] / "src" / "managed_bot.py")
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"fishing_bot": fake_base, "utils": fake_utils,
                                    "window_manager": fake_wm, "mss": fake_mss}):
            spec.loader.exec_module(module)
        cls.Bot = module.ManagedFishingBot
        cls.Guard = module.GuardedInput

    def config(self, key="cook", recoveries=2):
        return {"operations": {"start_spacing_seconds": 0, "max_recoveries": recoveries,
                                "recovery_cooldown": 0,
                                "workflows": {key: {"enabled": True, "steps": [{"action": "expect", "template": "verified.png", "settle": 0}]}}}}

    def test_recovery_budget_and_single_final_callback(self):
        bot = self.Bot(self.config())
        bot._port = Mock()
        bot._port.attempt.return_value = True
        bot.start()
        self.assertEqual(bot.total_games, 3)
        self.assertEqual(bot.metrics.snapshot()["recoveries"], 2)
        bot.on_bot_stop.assert_called_once_with(0)
        self.assertFalse(bot.running)
        bot.mouse_backend.close.assert_called_once()

    def test_failed_workflow_does_not_restart_or_refill_estimate(self):
        bot = self.Bot(self.config("restock"), reason="bait_depleted", bait=0)
        bot._port = Mock()
        bot._port.attempt.side_effect = OSError("bad image")
        bot.start()
        self.assertEqual(bot.total_games, 0)
        self.assertEqual(bot.bait_counter, 0)
        self.assertEqual(bot.stop_reason, "automation_error")
        bot.on_bot_stop.assert_called_once()

    def test_zero_bait_never_resets_without_verified_restock(self):
        bot = self.Bot({"operations": {"start_spacing_seconds": 0}}, bait=0)
        bot.start()
        self.assertEqual(bot.bait_counter, 0)
        self.assertEqual(bot.total_games, 0)

    def test_stop_before_delayed_start_never_runs_worker(self):
        bot = self.Bot(self.config())
        bot.stop()
        bot.start()
        self.assertEqual(bot.total_games, 0)
        bot.on_bot_stop.assert_called_once()

    def test_guard_suppresses_click_but_allows_release_on_stop(self):
        bot = self.Bot(self.config())
        underlying = bot.human.wrapped
        bot.stop()
        with self.assertRaises(RuntimeError):
            bot.human.click()
        underlying.click.assert_not_called()
        bot.human.mouse_up()
        underlying.mouse_up.assert_called_once()

    def test_session_limit_cancels_a_paused_worker(self):
        bot = self.Bot({"operations": {"session_minutes": 1}})
        bot._session_started = -10000000
        bot.paused = True
        bot.service_limits()
        self.assertTrue(bot._halt.is_set())
        self.assertFalse(bot.running)
        self.assertEqual(bot.stop_reason, "session_limit")
