import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
try:
    from PySide6.QtWidgets import QApplication
    from telegram_ui import TelegramTab, SERVICE
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False


@unittest.skipUnless(QT_AVAILABLE, "Qt is not installed")
class TelegramUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"LOCALAPPDATA": self.temp.name})
        self.env.start()
        self.vault = MagicMock()
        self.vault.get_password.return_value = None
        self.backend = patch.object(TelegramTab, "vault", return_value=self.vault)
        self.backend.start()
        self.tab = TelegramTab()

    def tearDown(self):
        self.tab.close()
        self.backend.stop()
        self.env.stop()
        self.temp.cleanup()

    def test_save_keeps_token_out_of_settings(self):
        token = "12345:" + "x" * 30
        self.tab.token.setText(token)
        self.tab.chat.setText("12345")
        self.tab.save()
        self.vault.set_password.assert_called_once_with(SERVICE, "bot_token", token)
        self.assertEqual(json.loads(self.tab.settings_path.read_text()), {"chat_id": "12345"})

    def test_failed_vault_does_not_fall_back_to_file(self):
        self.vault.set_password.side_effect = RuntimeError("sensitive detail")
        self.tab.token.setText("12345:" + "x" * 30)
        self.tab.chat.setText("12345")
        self.tab.save()
        self.assertFalse(self.tab.settings_path.exists())
        self.assertNotIn("sensitive detail", self.tab.status.text())

    def test_cancel_chat_choice_keeps_existing_recipient(self):
        self.tab.chat.setText("999")
        with patch("telegram_ui.QInputDialog.getItem", return_value=("", False)):
            self.tab.result("chats", {"1": "Bir", "2": "İki"})
        self.assertEqual(self.tab.chat.text(), "999")
