# Hand Steering Controller - 1-Line Installer & Launcher
$ErrorActionPreference = "Stop"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "   Hand Steering Controller - Automated Setup     " -ForegroundColor Yellow
Write-Host "==================================================" -ForegroundColor Cyan

# 1. Target Directory
$InstallDir = "$env:LOCALAPPDATA\HandSteer"
if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

Write-Host "[1/4] Downloading latest version from GitHub..." -ForegroundColor Green
$ZipUrl = "https://github.com/Sabir7869/Hand-Steering-Controller/archive/refs/heads/main.zip"
$ZipPath = "$env:TEMP\hand_steer.zip"

try {
    Invoke-WebRequest -Uri $ZipUrl -OutFile $ZipPath -UseBasicParsing
    Expand-Archive -Path $ZipPath -DestinationPath "$env:TEMP\hand_steer_extracted" -Force
    Copy-Item -Path "$env:TEMP\hand_steer_extracted\Hand-Steering-Controller-main\*" -Destination $InstallDir -Recurse -Force
    Remove-Item $ZipPath -Force -ErrorAction SilentlyContinue
    Remove-Item "$env:TEMP\hand_steer_extracted" -Recurse -Force -ErrorAction SilentlyContinue
} catch {
    Write-Host "[INFO] Downloading standalone files..." -ForegroundColor Yellow
    # Fallback to local files if running locally
    if (Test-Path "$PSScriptRoot\main.py") {
        Copy-Item -Path "$PSScriptRoot\*" -Destination $InstallDir -Recurse -Force
    }
}

# 2. Virtual Environment Setup
Set-Location $InstallDir
if (-not (Test-Path "$InstallDir\.venv")) {
    Write-Host "[2/4] Setting up isolated Python environment..." -ForegroundColor Green
    python -m venv .venv
}

# 3. Dependencies Installation
Write-Host "[3/4] Installing dependencies (MediaPipe, OpenCV, etc.)..." -ForegroundColor Green
& "$InstallDir\.venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
& "$InstallDir\.venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet

# 4. Create global command shortcut in user's profile
$BinDir = "$env:LOCALAPPDATA\Microsoft\WindowsApps"
$BatchFile = "$BinDir\hand-steer.cmd"
$BatchContent = @"
@echo off
"$InstallDir\.venv\Scripts\python.exe" "$InstallDir\main.py" %*
"@
Set-Content -Path $BatchFile -Value $BatchContent -Force

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " Setup Complete! Launching Controller...         " -ForegroundColor Green
Write-Host " Next time, simply type 'hand-steer' anywhere!   " -ForegroundColor Yellow
Write-Host "==================================================" -ForegroundColor Cyan

# 5. Launch application
& "$InstallDir\.venv\Scripts\python.exe" "$InstallDir\main.py"
