import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from remote_protocol import Countdown, command_from_update, stats_report


def update(uid=10, text="/start", owner=123, date=101):
    return {"update_id": uid, "message": {"date": date, "text": text,
            "chat": {"type": "private", "id": owner}, "from": {"id": owner}}}


class ProtocolTests(unittest.TestCase):
    def parse(self, value):
        return command_from_update(value, "123", "demo_bot", 100, now=105)

    def test_owner_command(self):
        self.assertEqual(self.parse(update()), ("/start", ""))
        self.assertEqual(self.parse(update(text="/pm merhaba")), ("/pm", "merhaba"))

    def test_rejects_other_owner_group_forward_and_edits(self):
        self.assertIsNone(self.parse(update(owner=999)))
        u = update(); u["message"]["chat"]["type"] = "group"
        self.assertIsNone(self.parse(u))
        u = update(); u["message"]["from"]["id"] = 999
        self.assertIsNone(self.parse(u))
        u = update(); u["message"]["forward_origin"] = {"type": "user"}
        self.assertIsNone(self.parse(u))
        self.assertIsNone(self.parse({"edited_message": update()["message"]}))

    def test_rejects_stale_and_misdirected_commands(self):
        self.assertIsNone(self.parse(update(date=99)))
        self.assertIsNone(command_from_update(update(), "123", "demo_bot", 100, now=200))
        self.assertIsNone(self.parse(update(text="/stop@other_bot")))
        self.assertEqual(self.parse(update(text="/stop@demo_bot")), ("/stop", ""))

    def test_timer_is_one_shot_and_cancelable(self):
        now = [0]
        timer = Countdown(lambda: now[0])
        timer.arm("1,5")
        now[0] = 89
        self.assertFalse(timer.due())
        now[0] = 90
        self.assertTrue(timer.due())
        self.assertFalse(timer.due())
        timer.arm(1)
        timer.cancel()
        now[0] = 1000
        self.assertFalse(timer.due())

    def test_invalid_timer_values(self):
        for value in ["", "nan", "inf", "-1", "0", "10081"]:
            with self.assertRaises(ValueError):
                Countdown().arm(value)

    def test_rounds_never_become_fish_count(self):
        text = stats_report(3661, [{"games": 500, "bait": 20, "bait_used": 500}], 1, 4000)
        self.assertIn("01:01:01", text)
        self.assertIn("ölçülmüyor", text)
        text = stats_report(10, [{"games": 20, "fish": 3, "fish_measured": True}], 1, 10)
        self.assertIn("görsel doğrulama): 3", text)
