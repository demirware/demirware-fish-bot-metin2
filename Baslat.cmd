@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Once Kur.cmd dosyasini calistirin.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" src\qt_gui.py
if errorlevel 1 pause
