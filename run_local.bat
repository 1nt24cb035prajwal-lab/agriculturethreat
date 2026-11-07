@echo off
setlocal
cd /d "%~dp0"

set "PYTHON=python"
if exist ".venv\Scripts\python.exe" set "PYTHON=.venv\Scripts\python.exe"

"%PYTHON%" -c "import fastapi, uvicorn" >nul 2>&1
if errorlevel 1 (
    echo Backend dependencies are missing.
    echo Run these commands from the repository root:
    echo   python -m venv .venv
    echo   .venv\Scripts\python.exe -m pip install -r backend\requirements.txt
    exit /b 1
)

start "Agriculture Threat Fusion" /min "%PYTHON%" -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
powershell -NoProfile -Command "$uri = 'http://localhost:8000/api/health'; for ($i = 0; $i -lt 120; $i++) { try { $response = Invoke-WebRequest -Uri $uri -TimeoutSec 1; if ($response.StatusCode -eq 200) { Start-Process 'http://localhost:8000'; exit 0 } } catch { }; Start-Sleep -Seconds 1 }; Write-Error 'The app did not become ready. Check the Agriculture Threat Fusion server window for errors.'; exit 1"
if errorlevel 1 exit /b 1
