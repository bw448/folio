@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo [Folio] Python venv not found. Run: python -m venv .venv
  pause
  exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" launcher.py
