@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem Builds a standalone folder "dist\SimForge Studio V3" (no Python needed to run it).
rem Run "SimForge Studio V3.bat" once first.
if not exist ".venv\Scripts\python.exe" (
    echo Run "SimForge Studio V3.bat" once first / Lance d abord "SimForge Studio V3.bat" une fois.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m pip install pyinstaller
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --windowed --name "SimForge Studio V3" ^
    --icon simforge_studio.ico --add-data "simforge_studio.png;." ^
    --add-data "firmware;firmware" --collect-all sdl2dll --collect-all esptool --hidden-import hid --hidden-import serial.tools.list_ports simforge_studio.py
echo.
echo Done / Termine : dist\SimForge Studio V3\SimForge Studio V3.exe
pause
