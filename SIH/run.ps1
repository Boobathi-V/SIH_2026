Write-Host "Starting SIH26038 Diabetic Retinopathy System..." -ForegroundColor Cyan
Start-Process python -ArgumentList "api.py"
Set-Location "SIH\dr-screen"
Start-Process npm -ArgumentList "run dev"
Write-Host "Backend (http://127.0.0.1:8000) and Frontend (http://localhost:5173) launched!" -ForegroundColor Green
