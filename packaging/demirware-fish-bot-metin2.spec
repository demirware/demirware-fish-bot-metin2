# Windows-only build. Kept separate from upstream packaging.
import os
root = os.path.dirname(SPECPATH)
a = Analysis(
    [os.path.join(root, 'src', 'qt_gui.py')],
    pathex=[os.path.join(root, 'src')],
    binaries=[], datas=[(os.path.join(root, 'assets'), 'assets')],
    hiddenimports=['pynput.keyboard', 'pynput.mouse', 'numba', 'llvmlite',
                   'jigsaw_solver.deterministic', 'PySide6.QtSvg', 'keyring.backends.Windows'],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='DemirwareFishBotMetin2-Dev',
          debug=False, strip=False, upx=False, console=True)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='DemirwareFishBotMetin2-Dev')
