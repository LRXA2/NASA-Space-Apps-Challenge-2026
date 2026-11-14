[CmdletBinding()]
param(
    [string]$Region = "Haworth",
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot

function Invoke-CheckedStep {
    param(
        [Parameter(Mandatory)]
        [string]$Name,
        [Parameter(Mandatory)]
        [scriptblock]$Command
    )

    Write-Host "`n==> $Name" -ForegroundColor Cyan
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE."
    }
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is not installed or is not on PATH. Install it from https://docs.astral.sh/uv/."
}
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
    throw "npm is not installed or is not on PATH. Install Node.js 22 or newer."
}

if (-not $SkipInstall) {
    Invoke-CheckedStep "Synchronizing locked Python dependencies" {
        uv sync --locked --all-extras
    }
}

Invoke-CheckedStep "Running the integrated Moon pipeline for $Region" {
    uv run --locked --all-extras python -m integration.run_all --region $Region
}

$regionSlug = ($Region.Trim().ToLowerInvariant() -replace '[^a-z0-9]+', '-').Trim('-')
Invoke-CheckedStep "Exporting validated $Region data for the web app" {
    uv run --locked --all-extras python app/scripts/export_data.py --region $regionSlug
}

if (-not $SkipInstall) {
    Invoke-CheckedStep "Installing locked web dependencies" {
        npm.cmd ci --prefix app
    }
}

Invoke-CheckedStep "Building the production web app" {
    npm.cmd run build --prefix app
}

Write-Host "`nDemo preparation completed successfully." -ForegroundColor Green
Write-Host "Start it with: npm.cmd run dev --prefix app"

