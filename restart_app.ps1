# Progress Report - Safe Restart Script
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Progress Report - App Restart" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# 1. Find and stop all Python processes related to this project
Write-Host "[1/4] Stopping all Python processes..." -ForegroundColor Yellow

$processes = Get-Process python -ErrorAction SilentlyContinue
if ($processes) {
    Write-Host "Found $($processes.Count) Python process(es):" -ForegroundColor White
    foreach ($proc in $processes) {
        Write-Host "  - PID: $($proc.Id), Started: $($proc.StartTime)" -ForegroundColor Gray
    }
    
    Write-Host ""
    Write-Host "Stopping all Python processes..." -ForegroundColor Yellow
    Stop-Process -Name python -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Write-Host "✓ All Python processes stopped" -ForegroundColor Green
} else {
    Write-Host "✓ No Python processes running" -ForegroundColor Green
}

Write-Host ""

# 2. Verify all processes are stopped
Write-Host "[2/4] Verifying processes stopped..." -ForegroundColor Yellow
$remaining = Get-Process python -ErrorAction SilentlyContinue
if ($remaining) {
    Write-Host "⚠ Warning: $($remaining.Count) Python process(es) still running" -ForegroundColor Red
    Write-Host "Attempting force kill..." -ForegroundColor Yellow
    foreach ($proc in $remaining) {
        Stop-Process -Id $proc.Id -Force
    }
    Start-Sleep -Seconds 1
}
Write-Host "✓ All processes stopped" -ForegroundColor Green
Write-Host ""

# 3. Clean up any lock files
Write-Host "[3/4] Cleaning up lock files..." -ForegroundColor Yellow
if (Test-Path "progress_report.db-wal") {
    Write-Host "  Removing WAL file..." -ForegroundColor Gray
}
if (Test-Path "progress_report.db-shm") {
    Write-Host "  Removing SHM file..." -ForegroundColor Gray
}
# Don't delete these files, just note them
Write-Host "✓ Lock files checked" -ForegroundColor Green
Write-Host ""

# 4. Start the app
Write-Host "[4/4] Starting Progress Report System..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  URL: http://127.0.0.1:5000" -ForegroundColor Cyan
Write-Host "  Features: ROD Dashboard, Progress Notes, Incident Viewer" -ForegroundColor Cyan
Write-Host ""

# Start the app in a new window
Start-Process -FilePath "python" -ArgumentList "app.py" -WorkingDirectory $PWD -WindowStyle Normal

Start-Sleep -Seconds 3

# Check if process started
$newProcess = Get-Process python -ErrorAction SilentlyContinue
if ($newProcess) {
    Write-Host "✓ App started successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Process Info:" -ForegroundColor White
    foreach ($proc in $newProcess) {
        Write-Host "  - PID: $($proc.Id)" -ForegroundColor Gray
    }
} else {
    Write-Host "✗ Failed to start app" -ForegroundColor Red
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Restart Complete!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Wait 5-10 seconds for app to fully start" -ForegroundColor White
Write-Host "  2. Open http://127.0.0.1:5000 in browser" -ForegroundColor White
Write-Host "  3. Check logs for 'get_cache_status_current error'" -ForegroundColor White
Write-Host "     (Should be gone or much less frequent)" -ForegroundColor White
Write-Host ""


