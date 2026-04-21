@echo off
setlocal

cd /d "%~dp0"

REM =========================
REM Cek Python
REM =========================
where python >nul 2>nul
if errorlevel 1 (
    echo.
    echo   Python 3.10 or newer is required, but was not found on PATH.
    echo.
    echo   Download and install it from:
    echo       https://www.python.org/downloads/
    echo.
    echo   During install, make sure to check "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

REM =========================
REM Buat venv jika belum ada
REM =========================
if not exist ".venv\Scripts\python.exe" (
    echo.
    echo   First-time setup: creating virtual environment...
    echo   (this only happens once and takes about a minute)
    echo.
    python -m venv .venv
    if errorlevel 1 (
        echo.
        echo   Failed to create the virtual environment.
        pause
        exit /b 1
    )
)

REM =========================
REM Aktifkan venv
REM =========================
call ".venv\Scripts\activate.bat"

REM =========================
REM Install dependencies
REM =========================
echo.
echo   Checking dependencies...
pip install --quiet --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
    echo.
    echo   Dependency install failed. Check your internet connection and try again.
    pause
    exit /b 1
)

REM =========================
REM Jalankan script
REM =========================
echo.
echo   Running cari.py...
echo.

python cari.py
if errorlevel 1 (
    echo.
    echo   Script exited with an error.
) else (
    echo.
    echo   Done.
)

echo.
pause