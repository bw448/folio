@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\pyinstaller.exe" (
  echo [Folio] 先安装打包依赖：.venv\Scripts\pip install pyinstaller
  pause
  exit /b 1
)
.venv\Scripts\pyinstaller.exe --noconfirm --clean Folio.spec
if errorlevel 1 (
  echo 打包失败，查看上方 PyInstaller 日志。
  pause
  exit /b 1
)
echo.
echo 完成：dist\Folio\Folio.exe
pause
