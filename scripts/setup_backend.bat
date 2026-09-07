@echo off
REM DepthWizard — Python backend dependency installer
REM Run this once after installing DepthWizard to set up the Python backend.

echo ========================================================
echo  DepthWizard Python Backend Setup
echo ========================================================
echo.
echo This script installs the required Python packages for
echo the DepthWizard depth estimation backend.
echo.
echo Required: Python 3.11 or newer (python.org)
echo.

REM Find Python
set PYTHON_EXE=
where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    for /f "tokens=*" %%i in ('where python') do set PYTHON_EXE=%%i
)

REM Check LOCALAPPDATA\Programs\Python
if "%PYTHON_EXE%"=="" (
    for /d %%d in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
        if exist "%%d\python.exe" set PYTHON_EXE=%%d\python.exe
    )
)

if "%PYTHON_EXE%"=="" (
    echo ERROR: Python not found.
    echo.
    echo Please install Python 3.11 or newer from:
    echo   https://www.python.org/downloads/
    echo.
    echo IMPORTANT: During installation, check "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

echo Found Python: %PYTHON_EXE%
"%PYTHON_EXE%" --version
echo.

echo Installing required packages...
echo.
"%PYTHON_EXE%" -m pip install --upgrade pip
"%PYTHON_EXE%" -m pip install pydantic>=2.0 Pillow>=11 rasterio>=1.4 numpy>=1.24

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Package installation failed.
    echo.
    echo Try running this script as Administrator, or manually run:
    echo   pip install pydantic Pillow rasterio numpy
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================================
echo  Setup complete! DepthWizard backend is ready.
echo ========================================================
echo.
echo You can now launch DepthWizard from your Desktop or Start Menu.
echo.
pause
