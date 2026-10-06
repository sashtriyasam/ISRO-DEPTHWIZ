@echo off
setlocal EnableDelayedExpansion
REM DepthWizard — Python backend setup (managed runtime + DA-V2 model)
REM Run this once after installing DepthWizard.
REM
REM Creates an isolated runtime in %LOCALAPPDATA%\DepthWizard\runtime,
REM installs the DepthWizard engine with the DA-V2 extra (torch, opencv),
REM provisions the pinned Depth Anything V2 source and the SHA-verified
REM checkpoint into %APPDATA%\DepthWizard. The desktop app uses this
REM runtime automatically.

echo ========================================================
echo  DepthWizard Python Backend Setup
echo ========================================================
echo.
echo Requires Python 3.11 or newer (https://www.python.org/downloads/)
echo and an internet connection for this one-time setup.
echo.

set "PYTHON_EXE="

REM 1) Python launcher (python.org installs register it).
for %%V in (3.13 3.12 3.11) do (
    if not defined PYTHON_EXE (
        for /f "usebackq delims=" %%P in (`py -%%V -c "import sys; print(sys.executable)" 2^>nul`) do (
            if not defined PYTHON_EXE set "PYTHON_EXE=%%P"
        )
    )
)

REM 2) Per-user python.org installs, newest first by numeric version.
if not defined PYTHON_EXE (
    for %%V in (313 312 311) do (
        if not defined PYTHON_EXE (
            if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" (
                set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe"
            )
        )
    )
)

REM 3) python on PATH, skipping the Microsoft Store alias stub (WindowsApps).
if not defined PYTHON_EXE (
    for /f "usebackq delims=" %%P in (`where python 2^>nul`) do (
        if not defined PYTHON_EXE (
            echo %%P | findstr /i "WindowsApps" >nul
            if errorlevel 1 set "PYTHON_EXE=%%P"
        )
    )
)

if not defined PYTHON_EXE goto :no_python

"%PYTHON_EXE%" -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if errorlevel 1 (
    echo ERROR: "%PYTHON_EXE%" is older than Python 3.11.
    goto :no_python
)

echo Using Python: %PYTHON_EXE%
"%PYTHON_EXE%" --version
echo.

set "RUNTIME_DIR=%LOCALAPPDATA%\DepthWizard\runtime"
set "PROJECT_ROOT=%~dp0.."

echo Provisioning the managed runtime (this downloads torch and the DA-V2
echo model once; it can take several minutes)...
echo.
"%PYTHON_EXE%" "%~dp0provision_runtime.py" --runtime-dir "%RUNTIME_DIR%" --project-root "%PROJECT_ROOT%" --mode dav2 --fetch-checkpoint --no-editable --pretty
if errorlevel 1 (
    echo.
    echo ERROR: Provisioning did not complete. The JSON status above names the
    echo failing step. Check your internet connection and run this script again;
    echo completed steps are reused.
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================================
echo  Setup complete. DepthWizard will use:
echo    %RUNTIME_DIR%
echo ========================================================
echo.
pause
exit /b 0

:no_python
echo ERROR: No usable Python 3.11+ was found.
echo.
echo Install Python 3.11 or newer from https://www.python.org/downloads/
echo (check "Add Python to PATH"), then run this script again.
echo.
pause
exit /b 1
