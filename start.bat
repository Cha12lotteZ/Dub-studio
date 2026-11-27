@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv\Scripts\dubstudio.exe (
  echo ยังไม่ได้ติดตั้ง ดับเบิลคลิก install.bat ก่อน
  pause
  exit /b 1
)
.venv\Scripts\dubstudio.exe serve
pause
