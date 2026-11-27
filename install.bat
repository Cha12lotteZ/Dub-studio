@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
rem ติดตั้งสตูดิโอพากเสียง (Windows) ไม่ต้องมี Python หรือ ffmpeg ในเครื่องก่อน

where uv >nul 2>nul
if errorlevel 1 (
  echo กำลังติดตั้ง uv ^(ตัวจัดการ Python^)...
  powershell -ExecutionPolicy Bypass -NoProfile -Command "irm https://astral.sh/uv/install.ps1 | iex"
)
set "PATH=%USERPROFILE%\.local\bin;%PATH%"

echo กำลังเตรียม Python 3.11 และแพ็กเกจหลัก...
uv venv --python 3.11 --allow-existing .venv || goto fail
uv pip install --python .venv\Scripts\python.exe -e . || goto fail

if "%DUB_INSTALL_AI%"=="1" goto ai
if "%DUB_INSTALL_AI%"=="0" goto done
choice /c YN /m "ติดตั้งส่วน AI ด้วยไหม (ถอดบท แยกเสียง พิมพ์บทให้พูด ใช้พื้นที่ประมาณ 2-3 GB)"
if errorlevel 2 goto done
:ai
uv pip install --python .venv\Scripts\python.exe -e ".[ai]" || goto fail

:done
echo.
echo เสร็จแล้ว ดับเบิลคลิก start.bat เพื่อเปิดแอป
pause
exit /b 0

:fail
echo.
echo ติดตั้งไม่สำเร็จ ลองรันอีกครั้ง หรือส่งข้อความด้านบนมาให้ดู
pause
exit /b 1
