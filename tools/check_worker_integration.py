"""Run one real fishing-loop round against synthetic frames and fake OS input."""
import ctypes
from pathlib import Path
import sys
import types
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
user32 = Mock()
user32.IsWindow.return_value = True
user32.GetForegroundWindow.return_value = 42
ctypes.windll = types.SimpleNamespace(user32=user32, shcore=Mock())
auto = types.ModuleType("pyautogui")
for name in ("moveTo", "mouseDown", "mouseUp", "click"):
    setattr(auto, name, Mock())
auto.position = lambda: (0, 0)
sys.modules["pyautogui"] = auto
gw = types.ModuleType("pygetwindow")
gw.Win32Window = object
sys.modules["pygetwindow"] = gw
keys = types.ModuleType("pynput.keyboard")
keys.Controller = Mock
keys.Key = types.SimpleNamespace(**{key: key for key in ("ctrl", "space", "f1", "f2", "f3", "f4")})
pynput = types.ModuleType("pynput")
pynput.keyboard = keys
sys.modules["pynput"] = pynput
sys.modules["pynput.keyboard"] = keys
screen = types.ModuleType("mss")
screen.mss = Mock()
sys.modules["mss"] = screen

import cv2
import numpy as np
from managed_bot import ManagedFishingBot
from window_manager import WindowManager

wm = WindowManager()
wm.selected_window = types.SimpleNamespace(_hWnd=42, left=0, top=0, width=800, height=600)
config = {"input_backend": "pyautogui", "bait_quantity": 1, "human_like_clicking": False,
          "auto_fish_handling": False, "operations": {"start_spacing_seconds": 0, "poll_interval": .01}}
bot = ManagedFishingBot(None, config, wm, bait_counter=1, bait_keys=["1"])
bot.on_bot_stop = Mock()
bot.on_status_update = print
bot._startup_scan_and_process_all_pages = lambda: None
bot._scan_empty_slots = lambda frame: [(1, 1)]
hsv = np.zeros((180, 180, 3), dtype=np.uint8)
hsv[:] = (102, 210, 220)
hsv[86:95, 86:95] = (103, 138, 120)
active = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
closed = np.full_like(active, 30)
count = [0]
def capture(area):
    if area == "full":
        return active
    if area == "inventory":
        return closed
    count[0] += 1
    return active if count[0] <= 2 else closed
bot._capture = capture
bot.start()
assert bot.total_games == 1, bot.total_games
assert bot.bait_counter == 0, bot.bait_counter
assert auto.mouseDown.call_count == 1, auto.mouseDown.call_count
assert auto.mouseUp.call_count == 1, auto.mouseUp.call_count
assert not bot.running
bot.on_bot_stop.assert_called_once_with(0)
print("Real worker integration: one synthetic round, one click, final callback once. No OS input sent.")
