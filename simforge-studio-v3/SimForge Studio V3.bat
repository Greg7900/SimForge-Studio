@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "VENV=%~dp0.venv"

if exist "%VENV%\Scripts\pythonw.exe" goto run

echo ============================================================
echo  SimForge Studio V3 - first start: installing (2-3 min)
echo  Premier lancement : installation (2-3 min)
echo ============================================================
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 -m venv "%VENV%"
) else (
    python -m venv "%VENV%"
)
if not exist "%VENV%\Scripts\python.exe" (
    echo.
    echo Python 3.9+ not found / introuvable.
    echo Install it from https://www.python.org/downloads/
    echo and tick "Add python.exe to PATH", then run this file again.
    pause
    exit /b 1
)
"%VENV%\Scripts\python.exe" -m pip install --upgrade pip
"%VENV%\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo Dependency install failed - check your internet connection.
    echo Echec de l'installation - verifie ta connexion internet.
    rmdir /s /q "%VENV%"
    pause
    exit /b 1
)

:run
start "" "%VENV%\Scripts\pythonw.exe" "%~dp0simforge_studio.py" %*
