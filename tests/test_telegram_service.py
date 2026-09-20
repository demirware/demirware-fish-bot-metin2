import sys
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from telegram_service import api_call, perform, private_chats, TelegramError

TOKEN = "12345:" + "x" * 30  # deliberately fake


class TelegramTests(unittest.TestCase):
    def test_invalid_token_never_reaches_network(self):
        with patch("telegram_service.urlopen") as http:
            with self.assertRaises(TelegramError):
                api_call("invalid", "getMe")
            http.assert_not_called()

    def test_send_validates_recipient(self):
        with patch("telegram_service.api_call") as api:
            with self.assertRaises(TelegramError):
                perform(TOKEN, "test", "not-a-chat")
            api.assert_not_called()

    def test_send_uses_explicit_recipient(self):
        with patch("telegram_service.api_call") as api:
            perform(TOKEN, "test", "12345")
            self.assertEqual(api.call_args.args[2]["chat_id"], "12345")

    def test_error_does_not_expose_token(self):
        error = HTTPError("https://api.telegram.org/bot" + TOKEN, 401, TOKEN, {}, None)
        with patch("telegram_service.urlopen", side_effect=error):
            with self.assertRaises(TelegramError) as ctx:
                api_call(TOKEN, "getMe")
            self.assertNotIn(TOKEN, str(ctx.exception))

    def test_chats_exclude_groups_and_keep_all_private_choices(self):
        updates = [{"message": {"chat": {"id": i, "type": kind, "first_name": str(i)}}}
                   for i, kind in [(1, "private"), (2, "private"), (-3, "group")]]
        self.assertEqual(set(private_chats(updates)), {"1", "2"})

    def test_api_uses_post_and_timeout(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"ok":true,"result":{"username":"demo_bot"}}'
        with patch("telegram_service.urlopen", return_value=response) as http:
            self.assertIn("demo_bot", perform(TOKEN, "check"))
            self.assertEqual(http.call_args.kwargs["timeout"], 12)
            self.assertEqual(http.call_args.args[0].get_method(), "POST")

    def test_failed_api_response(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"ok":false}'
        with patch("telegram_service.urlopen", return_value=response):
            with self.assertRaises(TelegramError):
                api_call(TOKEN, "getMe")
