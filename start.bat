@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [Folio] Python venv not found. Run: python -m venv .venv
  pause
  exit /b 1
)
start "Folio Server" cmd /k ".venv\Scripts\python.exe -m uvicorn server:app --app-dir . --host 127.0.0.1 --port 8788"
timeout /t 3 >nul
start "" "http://127.0.0.1:8788"
