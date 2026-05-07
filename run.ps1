# run.ps1 — start a local web server for the SPA and open the browser.
# Usage:   .\run.ps1            # default port 8765
#          .\run.ps1 -Port 9000

param(
    [int]$Port = 8765,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

if (-not (Test-Path "$root\data\data.json")) {
    Write-Warning "data\data.json not found. Place .msg/.eml files in dump\ and run: python scripts\fetch_emails_msg.py"
}

$url = "http://localhost:$Port/"
Write-Host ""
Write-Host "Safari Livetraining Recordings" -ForegroundColor Cyan
Write-Host "Serving $root" -ForegroundColor DarkGray
Write-Host "URL: $url" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop." -ForegroundColor DarkGray
Write-Host ""

if (-not $NoBrowser) {
    Start-Process $url
}

# Custom no-cache server so edits to JS/CSS/JSON show up without a hard refresh.
python "$root\scripts\serve.py" $Port
