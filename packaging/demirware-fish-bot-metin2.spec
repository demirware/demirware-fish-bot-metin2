# Build on Windows: one executable including Python and bundled assets.
import os
root = os.path.dirname(SPECPATH)
a = Analysis(
    [os.path.join(root, 'packaging', 'desktop_entry.py')],
    pathex=[os.path.join(root, 'src')],
    binaries=[], datas=[(os.path.join(root, 'assets'), 'assets')],
    hiddenimports=['pynput.keyboard._win32', 'pynput.mouse._win32',
                   'numba', 'llvmlite', 'jigsaw_solver.deterministic',
                   'PySide6.QtSvg', 'keyring.backends.Windows'],
    hookspath=[os.path.join(root, 'packaging', 'hooks')], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas,
          name='DemirwareFishBotMetin2', debug=False, strip=False,
          upx=False, console=False)
