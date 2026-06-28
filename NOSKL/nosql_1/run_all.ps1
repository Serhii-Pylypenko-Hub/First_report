param(
    [switch]$SkipLoad,
    [switch]$SkipIndexes
)

$ErrorActionPreference = "Stop"

function Read-DotEnv {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        throw ".env file not found. Copy .env.example to .env and set MONGO_URI."
    }

    $values = @{}
    Get-Content -LiteralPath $Path | ForEach-Object {
        $line = $_.Trim()
        if ($line -eq "" -or $line.StartsWith("#")) {
            return
        }

        $parts = $line.Split("=", 2)
        if ($parts.Length -eq 2) {
            $values[$parts[0].Trim()] = $parts[1].Trim()
        }
    }

    return $values
}

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
$python = Join-Path $root "venv311\Scripts\python.exe"
$mongosh = "mongosh"
$localMongosh = Join-Path $env:LOCALAPPDATA "Programs\mongosh\mongosh.exe"

if (-not (Test-Path -LiteralPath $python)) {
    Write-Host "Local venv not found. Creating venv311..." -ForegroundColor Yellow
    python -m venv --copies venv311
}

& $python -m pip install -r requirements.txt

if (-not (Get-Command $mongosh -ErrorAction SilentlyContinue)) {
    if (Test-Path -LiteralPath $localMongosh) {
        $mongosh = $localMongosh
    } else {
        throw "mongosh not found. Install MongoDB Shell or restart VS Code after installation."
    }
}

$envValues = Read-DotEnv ".env"
$mongoUri = $envValues["MONGO_URI"]
$csvPath = if ($envValues.ContainsKey("CSV_PATH")) { $envValues["CSV_PATH"] } else { "dataset.csv" }

if ([string]::IsNullOrWhiteSpace($mongoUri) -or $mongoUri -like "*user:password*") {
    throw "Set a real MONGO_URI in .env before running this script."
}

if (-not $SkipLoad -and -not (Test-Path -LiteralPath $csvPath)) {
    throw "CSV file not found: $csvPath. Put the Kaggle dataset here or set CSV_PATH in .env."
}

if (-not $SkipLoad) {
    Write-Host "[1/5] Loading CSV into tracks_raw..." -ForegroundColor Cyan
    & $python scripts/01_load_data.py
}

Write-Host "[2/5] Transforming tracks_raw into tracks..." -ForegroundColor Cyan
& $mongosh $mongoUri --file scripts/02_transform.js

Write-Host "[3/5] Running part 2 queries..." -ForegroundColor Cyan
& $mongosh $mongoUri --file queries/part2_queries.js

Write-Host "[4/5] Running part 3 aggregations..." -ForegroundColor Cyan
& $mongosh $mongoUri --file queries/part3_aggregations.js

if (-not $SkipIndexes) {
    Write-Host "[5/5] Running index/explain tasks..." -ForegroundColor Cyan
    & $mongosh $mongoUri --file queries/part4_indexes.js
} else {
    Write-Host "[5/5] Skipped index/explain tasks." -ForegroundColor Yellow
}

Write-Host "Done. Copy the actual query results and explain() metrics into README.md." -ForegroundColor Green
