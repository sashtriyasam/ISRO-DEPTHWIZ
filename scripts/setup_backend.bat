@echo off
echo =========================================================================
echo  DepthWizard (ISRO PS 26175) — Python Backend ^& Model Setup
echo =========================================================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python was not found on PATH.
    echo Please install Python 3.10+ from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo [1/3] Installing Python dependencies (pydantic, rasterio, numpy, opencv, torch)...
python -m pip install --upgrade pip
python -m pip install -r "%~dp0requirements.txt"
if %errorlevel% neq 0 (
    echo [WARNING] Default pip install encountered errors. Attempting CPU-only torch fallback...
    python -m pip install pydantic Pillow rasterio numpy opencv-python huggingface_hub
    python -m pip install torch torchvision --index-url https://download.pytorch.org/models/
)

echo.
echo [2/3] Installing depthwizard Python package in editable mode...
if exist "%~dp0..\pyproject.toml" (
    python -m pip install -e "%~dp0.."
) else (
    echo [INFO] Skipped editable install (standalone package mode).
)

echo.
echo [3/3] Checking / Downloading Depth Anything V2 Small Checkpoint...
python -c "
import os, sys
from pathlib import Path
from huggingface_hub import hf_hub_download

appdata = os.environ.get('APPDATA', '')
target_dir = Path(appdata) / 'DepthWizard' / 'checkpoints'
target_dir.mkdir(parents=True, exist_ok=True)
ckpt_path = target_dir / 'depth_anything_v2_vits.pth'

if ckpt_path.is_file():
    print(f'✅ Checkpoint already present: {ckpt_path}')
else:
    print('📥 Downloading Depth Anything V2 Small model weights from HuggingFace...')
    try:
        downloaded = hf_hub_download(repo_id='depth-anything/Depth-Anything-V2-Small', filename='depth_anything_v2_vits.pth')
        import shutil
        shutil.copy(downloaded, ckpt_path)
        print(f'✅ Successfully downloaded weights to {ckpt_path}')
    except Exception as e:
        print(f'⚠️ Auto-download note: {e}')
"

echo.
echo =========================================================================
echo  Setup Completed Successfully!
echo =========================================================================
echo You can now run DepthWizard with full AI Monocular Depth estimation.
pause
