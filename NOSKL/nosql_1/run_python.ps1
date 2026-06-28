$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot
$python = Join-Path $PSScriptRoot "venv311\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    Write-Host "Local venv not found. Creating venv311..." -ForegroundColor Yellow
    python -m venv --copies venv311
}

Write-Host "[1/2] Installing Python dependencies..." -ForegroundColor Cyan
& $python -m pip install -r requirements.txt

Write-Host "[2/2] Running full MongoDB homework in Python..." -ForegroundColor Cyan
& $python scripts/03_run_all_python.py
