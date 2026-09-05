@echo off
echo ====================================================
echo Starting SIH26038 Diabetic Retinopathy System...
echo ====================================================
start "DR Screening API (Backend)" cmd /k "python api.py"
cd SIH\dr-screen
start "DR Screening Frontend (Vite)" cmd /k "npm run dev"
echo Both Backend (http://127.0.0.1:8000) and Frontend (http://localhost:5173) are starting!
