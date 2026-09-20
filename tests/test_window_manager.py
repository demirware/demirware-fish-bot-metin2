"""Focus regression tests with a simulated Win32 API; no desktop input is sent."""

import ctypes
import importlib.util
from pathlib import Path
import sys
import threading
import types
import unittest
from unittest.mock import Mock, patch


class WindowFocusTests(unittest.TestCase):
    def setUp(self):
        self.user32 = Mock()
        self.user32.IsWindow.return_value = True
        self.user32.IsIconic.return_value = False
        self.user32.GetForegroundWindow.return_value = 99
        spec = importlib.util.spec_from_file_location(
            "_window_manager_focus_test",
            Path(__file__).resolve().parents[1] / "src" / "window_manager.py",
        )
        self.module = importlib.util.module_from_spec(spec)
        fake_gw = types.ModuleType("pygetwindow")
        fake_gw.Win32Window = object
        fake_utils = types.ModuleType("utils")
        fake_utils.DEBUG_PRINTS = False
        with patch.dict(sys.modules, {
            spec.name: self.module, "pygetwindow": fake_gw, "utils": fake_utils,
        }), patch.object(ctypes, "windll", types.SimpleNamespace(user32=self.user32), create=True):
            spec.loader.exec_module(self.module)
        # Replace the module's time reference, without changing global time.sleep.
        self.module.time = types.SimpleNamespace(sleep=Mock())
        self.manager = self.module.WindowManager()
        self.manager.selected_window = types.SimpleNamespace(_hWnd=42)

    def test_already_focused_avoids_activation_and_delay(self):
        self.user32.GetForegroundWindow.return_value = 42
        self.manager.activate_window()
        self.user32.SetForegroundWindow.assert_not_called()
        self.module.time.sleep.assert_not_called()

    def test_focus_can_be_acquired_on_later_attempt(self):
        self.user32.GetForegroundWindow.side_effect = [99, 99, 42]
        self.manager.activate_window()
        self.assertEqual(self.user32.SetForegroundWindow.call_count, 2)

    def test_force_activation_is_still_verified(self):
        self.user32.GetForegroundWindow.return_value = 42
        self.manager.activate_window(force_activate=True)
        self.user32.SetForegroundWindow.assert_called_once_with(42)

    def test_denied_focus_aborts_input_and_releases_lock(self):
        send_input = Mock()
        lock = threading.Lock()
        with self.assertRaises(self.module.WindowActivationError):
            with lock:
                self.manager.activate_window()
                send_input()
        send_input.assert_not_called()
        self.assertFalse(lock.locked())
        self.assertEqual(self.user32.SetForegroundWindow.call_count, 3)

    def test_no_selection_rejects_input(self):
        self.manager.selected_window = None
        with self.assertRaises(self.module.WindowActivationError):
            self.manager.activate_window()
        self.user32.SetForegroundWindow.assert_not_called()

    def test_destroyed_window_invalidates_cached_coordinates(self):
        self.user32.IsWindow.return_value = False
        self.manager._rect_cache = (10, 20, 800, 600)
        with self.assertRaises(self.module.WindowActivationError):
            self.manager.activate_window()
        self.assertIsNone(self.manager._rect_cache)
        self.user32.SetForegroundWindow.assert_not_called()

    def test_zero_window_handle_rejects_input(self):
        self.manager.selected_window._hWnd = 0
        with self.assertRaises(self.module.WindowActivationError):
            self.manager.activate_window()
        self.user32.SetForegroundWindow.assert_not_called()

    def test_minimized_window_is_restored_before_focus_check(self):
        self.user32.IsIconic.return_value = True
        self.user32.GetForegroundWindow.side_effect = [99, 42]
        self.manager.activate_window()
        self.user32.ShowWindow.assert_called_once_with(42, 9)

    def test_api_error_is_not_silently_ignored(self):
        error = OSError("Win32 unavailable")
        self.user32.IsWindow.side_effect = error
        with self.assertRaises(self.module.WindowActivationError) as caught:
            self.manager.activate_window()
        self.assertIs(caught.exception.__cause__, error)

    def test_repeated_activation_errors_cannot_fall_through(self):
        self.user32.SetForegroundWindow.side_effect = OSError("Denied")
        with self.assertRaises(self.module.WindowActivationError):
            self.manager.activate_window()
        self.assertEqual(self.user32.SetForegroundWindow.call_count, 3)


if __name__ == "__main__":
    unittest.main()
