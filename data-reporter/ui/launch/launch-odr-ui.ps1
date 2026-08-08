# Double-click / right-click "Run with PowerShell" launcher for the ODR
# chat UI (Windows, non-technical users). Equivalent to launch-odr-ui.bat
# but checks `uv` is on PATH first with a friendlier message.

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repoRoot

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "uv is not installed or not on PATH." -ForegroundColor Red
    Write-Host "Install it from https://docs.astral.sh/uv/ and try again." -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}

Write-Host "Starting Ops Data Reporter chat UI..."
uv run odr ui
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Something went wrong starting the UI - see the message above." -ForegroundColor Red
    Read-Host "Press Enter to close"
}
