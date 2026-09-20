@echo off
setlocal
cd /d "%~dp0"
py -3.12 -c "import struct; assert struct.calcsize('P') == 8" >nul 2>&1
if errorlevel 1 (
  echo Python 3.12 64-bit ve Python Launcher gerekli.
  echo Python kurulumundan sonra Kur.cmd dosyasini tekrar acin.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" py -3.12 -m venv .venv
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements-windows.txt
if errorlevel 1 goto failed
echo Kurulum tamamlandi. Baslat.cmd dosyasini acin.
pause
exit /b 0
:failed
echo Kurulum tamamlanamadi. Yukaridaki hata mesajini kaydedin.
pause
exit /b 1
