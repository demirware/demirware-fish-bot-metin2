"""Frozen desktop entry: writable state and visible startup failures."""
import ctypes
import os
from pathlib import Path
import sys
import traceback


def main():
    state = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'DemirwareFishBotMetin2'
    state.mkdir(parents=True, exist_ok=True)
    os.chdir(state)
    os.environ.setdefault('JIGSAW_SOLVER_CACHE_DIR', str(state / 'cache' / 'jigsaw'))
    os.environ.setdefault('NUMBA_CACHE_DIR', str(state / 'cache' / 'numba'))
    # Windowed PyInstaller builds have no stdout/stderr. Keep diagnostics usable.
    log = open(state / 'startup.log', 'a', encoding='utf-8', buffering=1)
    sys.stdout = sys.stderr = log
    try:
        import qt_gui
        if '--self-test' in sys.argv:
            if qt_gui.pyn_mouse is None or qt_gui.pyn_keyboard is None:
                raise RuntimeError(qt_gui._PYNPUT_IMPORT_ERROR)
            if qt_gui.FishingBot is None:
                raise RuntimeError('Fishing engine failed to import')
            from utils import get_resource_path
            if not Path(get_resource_path('assets/jigsaw/Jigsaw_piece2.png')).is_file():
                raise RuntimeError('Bundled assets missing')
            from PySide6.QtWidgets import QApplication
            app = QApplication([])
            window = qt_gui.FishbotWindow()
            window.show()
            app.processEvents()
            window.close()
            app.processEvents()
            print('SELF TEST OK')
            return 0
        return qt_gui.main()
    except Exception:
        traceback.print_exc()
        log.flush()
        if '--self-test' not in sys.argv:
            ctypes.windll.user32.MessageBoxW(None, f'Program başlatılamadı. Hata kaydı:\n{state / "startup.log"}', 'Demirware Fish Bot', 16)
        return 1


if __name__ == '__main__':
    sys.exit(main())
