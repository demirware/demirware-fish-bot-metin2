@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Once Kur.cmd dosyasini calistirin.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m PyInstaller --noconfirm packaging\demirware-fish-bot-metin2.spec
if errorlevel 1 (
  echo EXE derlenemedi. Hata mesajini kaydedin.
  pause
  exit /b 1
)
echo Sonuc: dist\DemirwareFishBotMetin2.exe
pause
