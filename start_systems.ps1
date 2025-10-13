# Progress Report - Dual System Startup (PowerShell)
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Progress Report - Dual System Startup" -ForegroundColor Cyan  
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Starting both systems simultaneously..." -ForegroundColor Yellow
Write-Host "Core System (ROD + Progress Notes): http://127.0.0.1:5000" -ForegroundColor Green
Write-Host "Admin System (Incident + Policy + FCM): http://127.0.0.1:5001" -ForegroundColor Green
Write-Host ""

# Start Core System
Write-Host "[1/2] Starting Core System..." -ForegroundColor Blue
Start-Process -FilePath "python" -ArgumentList "app.py" -WindowStyle Normal -WorkingDirectory $PWD

# Wait a moment
Start-Sleep -Seconds 2

# Start Admin System  
Write-Host "[2/2] Starting Admin System..." -ForegroundColor Blue
Start-Process -FilePath "python" -ArgumentList "admin_app.py" -WindowStyle Normal -WorkingDirectory "$PWD\admin_system"

Write-Host ""
Write-Host "✅ Both systems are starting up!" -ForegroundColor Green
Write-Host ""
Write-Host "🌐 Access URLs:" -ForegroundColor Cyan
Write-Host "  Core System:  http://127.0.0.1:5000" -ForegroundColor White
Write-Host "  Admin System: http://127.0.0.1:5001" -ForegroundColor White
Write-Host ""
Write-Host "📝 Note: Two Python processes are now running" -ForegroundColor Yellow
Write-Host "🔄 Wait a few seconds for systems to fully start" -ForegroundColor Yellow
Write-Host ""

# Wait for systems to start
Write-Host "Waiting for systems to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

Write-Host "Systems should be ready now!" -ForegroundColor Green
Write-Host ""
Write-Host "Press any key to continue..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
