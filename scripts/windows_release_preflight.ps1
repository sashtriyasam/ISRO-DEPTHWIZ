#Requires -Version 5.1
<#
.SYNOPSIS
    DepthWizard Windows Release Preflight - read-only environment inspection.
.DESCRIPTION
    Inspects the current Windows machine to determine whether the DepthWizard
    release prerequisites are satisfied. Outputs structured PASS/FAIL/WARN
    results for each check.
    This script MUST NOT install software, download files, modify PATH,
    modify environment variables, modify Python, modify checkpoint, or delete anything.
.EXAMPLE
    .\scripts\windows_release_preflight.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

$results = @()

function Add-Result {
    param([string]$Check, [string]$Status, [string]$Detail)
    $script:results += [PSCustomObject]@{ Check = $Check; Status = $Status; Detail = $Detail }
}

# 1. System Information
Add-Result "OS" "INFO" "$([System.Environment]::OSVersion.VersionString)"
Add-Result "Architecture" "INFO" "$env:PROCESSOR_ARCHITECTURE"
Add-Result "User" "INFO" "$env:USERDOMAIN\$env:USERNAME"

# 2. Python Validation
$pythonExe = $null
$pythonSource = "NOT_FOUND"

if ($env:DEPTHWIZARD_PYTHON -and (Test-Path $env:DEPTHWIZARD_PYTHON)) {
    $pythonExe = $env:DEPTHWIZARD_PYTHON
    $pythonSource = "DEPTHWIZARD_PYTHON env"
} else {
    $found = Get-Command python -ErrorAction SilentlyContinue
    if ($found) {
        $pythonExe = $found.Source
        $pythonSource = "python on PATH"
    }
}

if ($pythonExe) {
    Add-Result "Python Executable" "PASS" "$pythonExe (source: $pythonSource)"

    try {
        $versionOutput = & $pythonExe --version 2>&1
        $versionMatch = [regex]::Match($versionOutput, "Python (\d+)\.(\d+)\.(\d+)")
        if ($versionMatch.Success) {
            $major = [int]$versionMatch.Groups[1].Value
            $minor = [int]$versionMatch.Groups[2].Value
            $micro = [int]$versionMatch.Groups[3].Value
            if ($major -eq 3 -and $minor -ge 10) {
                Add-Result "Python Version" "PASS" "$major.$minor.$micro (>= 3.10 required)"
            } else {
                Add-Result "Python Version" "FAIL" "$major.$minor.$micro (>= 3.10 required)"
            }
        } else {
            Add-Result "Python Version" "WARN" "Could not parse: $versionOutput"
        }
    } catch {
        Add-Result "Python Version" "FAIL" "Failed to execute python --version"
    }

    $pkgs = @(
        @{ N = "torch"; I = "torch" },
        @{ N = "PIL (Pillow)"; I = "PIL" },
        @{ N = "numpy"; I = "numpy" },
        @{ N = "pydantic"; I = "pydantic" },
        @{ N = "depthwizard"; I = "depthwizard" },
        @{ N = "depthwizard.backends.depth_anything_v2"; I = "depthwizard.backends.depth_anything_v2" }
    )
    foreach ($p in $pkgs) {
        try {
            $r = & $pythonExe -c "import $($p.I); print(getattr(__import__('$($p.I)'), '__version__', 'ok'))" 2>&1
            if ($LASTEXITCODE -eq 0) {
                Add-Result "Package: $($p.N)" "PASS" "importable - $r"
            } else {
                Add-Result "Package: $($p.N)" "FAIL" "import failed"
            }
        } catch {
            Add-Result "Package: $($p.N)" "FAIL" "import error"
        }
    }

    try { $dwV = & $pythonExe -c "import depthwizard; print(depthwizard.__version__)" 2>&1; Add-Result "DepthWizard Version" "INFO" "$dwV" } catch { Add-Result "DepthWizard Version" "WARN" "Could not determine" }
    try { $tV = & $pythonExe -c "import torch; print(torch.__version__)" 2>&1; Add-Result "Torch Version" "INFO" "$tV" } catch { Add-Result "Torch Version" "WARN" "Could not determine" }
} else {
    Add-Result "Python Executable" "FAIL" "No Python found (checked DEPTHWIZARD_PYTHON env and PATH)"
    Add-Result "Python Version" "FAIL" "Skipped - no Python"
    Add-Result "Package: torch" "FAIL" "Skipped - no Python"
    Add-Result "Package: PIL (Pillow)" "FAIL" "Skipped - no Python"
    Add-Result "Package: numpy" "FAIL" "Skipped - no Python"
    Add-Result "Package: pydantic" "FAIL" "Skipped - no Python"
    Add-Result "Package: depthwizard" "FAIL" "Skipped - no Python"
    Add-Result "Package: depthwizard.backends.depth_anything_v2" "FAIL" "Skipped - no Python"
}

# 3. Checkpoint Validation
$expectedSHA = "715fade13be8f229f8a70cc02066f656f2423a59effd0579197bbf57860e1378"
$checkpointPaths = @("$env:APPDATA\DepthWizard\checkpoints\depth_anything_v2_vits.pth")

if ($env:DW_DAV2_CKPT -and (Test-Path $env:DW_DAV2_CKPT)) {
    $checkpointPaths = @($env:DW_DAV2_CKPT) + $checkpointPaths
}

$checkpointFound = $false
foreach ($cp in $checkpointPaths) {
    if (Test-Path $cp) {
        $checkpointFound = $true
        $actualSHA = (Get-FileHash $cp -Algorithm SHA256).Hash
        $fileSize = (Get-Item $cp).Length
        if ($actualSHA -eq $expectedSHA) {
            Add-Result "Checkpoint" "PASS" "Valid at $cp ($([math]::Round($fileSize / 1MB, 1)) MB)"
            Add-Result "Checkpoint SHA" "PASS" "$actualSHA"
        } else {
            Add-Result "Checkpoint" "FAIL" "INVALID at $cp - SHA mismatch"
            Add-Result "Checkpoint SHA" "FAIL" "Expected: $expectedSHA  Actual: $actualSHA"
        }
        break
    }
}

if (-not $checkpointFound) {
    Add-Result "Checkpoint" "FAIL" "MISSING - not found at any expected location"
    Add-Result "Checkpoint SHA" "FAIL" "Skipped - no checkpoint"
}

# 4. Backend Capability Validation
if ($pythonExe) {
    $serviceScript = Join-Path $PSScriptRoot "depthwiz_service.py"
    if (Test-Path $serviceScript) {
        try {
            $capsResult = echo '{"capabilities": true}' | & $pythonExe $serviceScript 2>&1
            $capsObj = $capsResult | ConvertFrom-Json
            $backends = $capsObj.capabilities.available_backends
            Add-Result "Service Capabilities" "PASS" "available_backends: $($backends -join ', ')"
            if ($backends -contains "depth-anything-v2-small") {
                Add-Result "DA-V2 Capability" "PASS" "depth-anything-v2-small is available"
            } else {
                Add-Result "DA-V2 Capability" "WARN" "depth-anything-v2-small NOT available (checkpoint missing or invalid)"
            }
        } catch {
            Add-Result "Service Capabilities" "FAIL" "Could not invoke service"
        }
    } else {
        Add-Result "Service Capabilities" "FAIL" "Service script not found"
    }
} else {
    Add-Result "Service Capabilities" "FAIL" "Skipped - no Python"
}

# 5. Node.js (informational)
$nodeFound = Get-Command node -ErrorAction SilentlyContinue
if ($nodeFound) {
    $nodeVersion = & node --version 2>&1
    Add-Result "Node.js" "INFO" "$nodeVersion"
} else {
    Add-Result "Node.js" "INFO" "Not found (not required for runtime)"
}

# 6. Output
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " DepthWizard Windows Release Preflight" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$passCount = @($results | Where-Object { $_.Status -eq "PASS" }).Count
$failCount = @($results | Where-Object { $_.Status -eq "FAIL" }).Count
$warnCount = @($results | Where-Object { $_.Status -eq "WARN" }).Count

foreach ($r in $results) {
    $color = switch ($r.Status) {
        "PASS" { "Green" }
        "FAIL" { "Red" }
        "WARN" { "Yellow" }
        "INFO" { "Cyan" }
        default { "White" }
    }
    Write-Host ("  [{0,-4}] " -f $r.Status) -ForegroundColor $color -NoNewline
    Write-Host "$($r.Check): $($r.Detail)"
}

Write-Host ""
Write-Host "--------------------------------------------" -ForegroundColor Cyan
Write-Host "  PASS: $passCount  FAIL: $failCount  WARN: $warnCount" -ForegroundColor $(if ($failCount -gt 0) { "Red" } else { "Green" })
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

if ($failCount -gt 0) {
    Write-Host "BLOCKERS REMAINING - resolve FAIL items before release acceptance." -ForegroundColor Red
} else {
    Write-Host "ALL CHECKS PASSED - ready for release witness validation." -ForegroundColor Green
}
