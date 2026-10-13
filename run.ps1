# DriveLens AI - Unified One-Click Launcher
# Runs both Frontend and Backend together on http://localhost:8000

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   DriveLens AI - Read-Only Document Intelligence Assistant" -ForegroundColor White
Write-Host "   Frontend & Backend Combined on: http://localhost:8000   " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

# Ensure we are in project root
Set-Location $PSScriptRoot

# Automatically open the browser to the unified app
Start-Process "http://localhost:8000"

# Start the unified FastAPI server (which serves both the API and the Next.js UI)
.\backend\venv\Scripts\uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
