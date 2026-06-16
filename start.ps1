# Run this from the repo root to start both servers at once
$py = "C:\Users\khals\AppData\Local\Programs\Python\Python312\python.exe"

Write-Host "Starting backend on http://localhost:8000 ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\backend'; & '$py' -m uvicorn main:app --reload"

Write-Host "Starting frontend on http://localhost:5173 ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\frontend'; npm run dev"

Write-Host "Both servers starting. Open http://localhost:5173 in your browser." -ForegroundColor Green
