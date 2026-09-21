import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace, ModuleType
from unittest.mock import Mock, patch
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
try:
    from PySide6.QtWidgets import QApplication, QWidget
    from session_control import SessionControl, TransitionWorker, checked_recipe
    from telegram_remote import TelegramListener
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False


@unittest.skipUnless(QT_AVAILABLE, "Qt is not installed")
class ControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.owner = QWidget()
        self.owner.config = {}
        self.owner.bots = {}
        self.owner.bot_threads = {}
        self.owner.window_stats = {}
        self.owner.dashboard = SimpleNamespace(window_rows=[])
        self.owner.telegram_tab = SimpleNamespace(send_remote=Mock(), listener=None)
        self.owner._jigsaw_dialog = None
        self.owner.selected_window_names = lambda: []
        self.owner.save_config = Mock()
        self.control = SessionControl(self.owner)
        self.control.timer.stop()
        self.owner.stop_all_bots = self.control.cancel_all
        self.owner.start_all_bots = Mock()

    def tearDown(self):
        self.control.cancel_all()
        self.owner.close()

    def test_start_error_returned_without_modal(self):
        self.owner.start_all_bots.side_effect = ValueError("Pencere seçilmedi")
        self.control.command("/start", "")
        self.assertIn("Pencere seçilmedi", self.owner.telegram_tab.send_remote.call_args.args[0])

    def test_stop_waits_for_thread_and_cancels_timer(self):
        thread = Mock()
        thread.is_alive.return_value = True
        self.owner.bot_threads[0] = thread
        self.control.countdown.arm(1)
        self.control.command("/stop", "")
        self.assertIsNone(self.control.countdown.remaining())
        self.control.tick()
        self.assertIsNotNone(self.control.pending)
        thread.is_alive.return_value = False
        self.control.tick()
        self.assertIsNone(self.control.pending)
        self.assertIn("Bot durduruldu", self.owner.telegram_tab.send_remote.call_args.args[0])

    def test_cancel_prevents_repeating_inflight_plan(self):
        self.control.restart_plan = {"repeat": True}
        self.control.cancel_timer()
        self.assertFalse(self.control.restart_plan["repeat"])

    def test_pm_does_not_send_game_input_or_save_draft(self):
        self.control.command("/pm", "test yanıtı")
        self.assertIn("Mesaj gönderilmedi", self.owner.telegram_tab.send_remote.call_args.args[0])
        self.owner.start_all_bots.assert_not_called()

    def test_cancelled_transition_never_resumes(self):
        self.control.worker = Mock()
        self.control.restart_plan = {"resume": True, "repeat": True, "success": True}
        self.control.cancel_all()
        self.control.transition_result(True, "success")
        self.control.transition_finished()
        self.owner.start_all_bots.assert_not_called()
        self.assertIn("iptal", self.owner.telegram_tab.send_remote.call_args.args[0])

    def test_timeout_prevents_desktop_transition(self):
        self.control.pending = {"kind": "character_select", "deadline": 0, "threads": []}
        with patch("session_control.TransitionWorker") as worker:
            self.control.tick()
            worker.assert_not_called()
        self.assertIsNone(self.control.pending)

    def test_new_transition_recipes_pass_profile_validation(self):
        from profile_validation import validate_profile
        recipe = {"enabled": True, "steps": [
            {"action": "key", "key": "esc", "template": "game.png"},
            {"action": "click", "template": "menu.png"},
            {"action": "expect", "template": "character-screen.png"}]}
        validated = validate_profile({"operations": {"workflows": {"character_select": recipe}}})
        self.assertTrue(validated["operations"]["workflows"]["character_select"]["enabled"])

    def test_transition_requires_action_and_distinct_success_image(self):
        recipe = {"enabled": True, "steps": [{"action": "expect", "template": "same.png"}]}
        with self.assertRaises(ValueError):
            checked_recipe({"operations": {"workflows": {"character_select": recipe}}}, "character_select")

    def test_failed_visual_verification_never_claims_success(self):
        bot = Mock()
        bot.sct = None
        base = ModuleType("managed_bot"); base.ManagedFishingBot = Mock(return_value=bot)
        wm = ModuleType("window_manager"); wm.WindowManager = Mock()
        worker = TransitionWorker([(0, object())], {}, {}, "character_select")
        results = []
        worker.completed.connect(lambda ok, text: results.append((ok, text)))
        with patch.dict(sys.modules, {"managed_bot": base, "window_manager": wm}), patch("session_control.WorkflowRunner") as runner:
            runner.return_value.run.side_effect = RuntimeError("Görsel bulunamadı")
            worker.run()
        self.assertFalse(results[0][0])
        self.assertNotIn("başarılı", results[0][1])
        bot.mouse_backend.close.assert_called_once()

    def test_listener_drops_backlog_and_duplicate_update(self):
        listener = TelegramListener("123:" + "x"*30, "123")
        received = []
        listener.command.connect(lambda *args: received.append(args))
        message = {"update_id": 11, "message": {"date": 101, "text": "/durum",
                   "chat": {"type": "private", "id": 123}, "from": {"id": 123}}}
        def api(token, method, payload=None):
            if method == "getMe": return {"username": "demo_bot"}
            if payload.get("offset") == -1: return [{"update_id": 10}]
            if payload.get("offset") == 11: return [message, message]
            listener.stop()
            return []
        with patch("telegram_remote.api_call", side_effect=api), patch("telegram_remote.time.time", return_value=100):
            listener.run()
        self.assertEqual(received, [("/durum", "")])
        self.assertEqual(listener.token, "")
