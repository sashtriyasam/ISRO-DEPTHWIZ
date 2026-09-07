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
echo Installing real depth-inference packages (CPU PyTorch stack)...
echo This download is large (~200 MB) and may take several minutes.
echo.
"%PYTHON_EXE%" -m pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision opencv-python

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo WARNING: ML package installation failed. The app will still run,
    echo but only the synthetic demo backend will be available (flat test
    echo pattern). Re-run this script later with network access, or see the
    echo in-app backend guidance. Continuing with core setup...
    echo.
) else (
    echo.
    echo ML packages installed. Verifying real-backend readiness...
    echo.
    "%PYTHON_EXE%" "%~dp0runtime_check.py" --require-dav2
)

echo.
echo NOTE: the M17 adapted model weights ship inside the installer
echo (no download needed); this script only provides the PyTorch stack
echo they run on.
echo.
echo ========================================================
echo  Setup complete! DepthWizard backend is ready.
echo ========================================================
echo.
echo You can now launch DepthWizard from your Desktop or Start Menu.
echo.
pause
