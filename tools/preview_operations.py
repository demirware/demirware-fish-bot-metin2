"""Offline Qt layout verification. Stub only OS integration; no game is run."""
import os
from pathlib import Path
import sys
import tempfile
import types

os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
wm = types.ModuleType("window_manager")
class WindowManager:
    @staticmethod
    def get_all_windows():
        return []
wm.WindowManager = WindowManager
sys.modules["window_manager"] = wm
backend = types.ModuleType("input_backend")
backend.probe_backend = lambda _: ("pyautogui", "Offline layout preview")
sys.modules["input_backend"] = backend

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
from PySide6.QtCore import QTimer
from qt_gui import FishbotWindow, build_qss, C
from operations_ui import WorkflowEditor

def main():
    output = ROOT / "docs" / "previews"
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    app.setStyleSheet(build_qss(C["accent"]))
    with tempfile.TemporaryDirectory() as directory:
        os.chdir(directory)
        window = FishbotWindow()
        window.show()
        app.processEvents()
        window.grab().save(str(output / "clients.png"))
        window._set_tab("operations")
        window.tabs_bar.setActive("operations")
        window.operations_tab.refresh()
        app.processEvents()
        window.grab().save(str(output / "operations.png"))
        editor = WorkflowEditor(window)
        editor.show()
        app.processEvents()
        editor.grab().save(str(output / "workflow-editor.png"))
        assert window.operations_tab.table.rowCount() == 8
        assert window.stack.count() == 4
        assert window.operations_tab.table.cellWidget(0, 8).isEnabled() is False
        window.save_config()
        assert Path("bot_config.json").is_file()
        editor.close()
        window.close()
    print("Qt layout and idle control checks passed; screenshots:", output)

if __name__ == "__main__":
    main()
