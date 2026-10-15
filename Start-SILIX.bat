@echo off
title SILIX Studio Standalone Server
color 0b
echo ===================================================================
echo                     SILIX - Silicon RTL Studio
echo               (Running Standalone Outside Antigravity)
echo ===================================================================
echo.
cd /d "C:\Users\gunar\.gemini\antigravity\scratch\rtl-cloud-api"

echo [1/2] Starting backend server on port 8000...
start "SILIX Backend" /min "C:\Users\gunar\.gemini\antigravity\scratch\rtl-cloud-api\.venv\Scripts\uvicorn.exe" app.main:app --host 0.0.0.0 --port 8000

timeout /t 3 /nobreak >nul

echo [2/2] Connecting Cloudflare internet tunnel...
echo.
echo ===================================================================
echo NOTE: You can now CLOSE Antigravity!
echo The public link will STAY ONLINE as long as this window is open.
echo To turn off SILIX, simply close this window.
echo ===================================================================
echo.
"C:\Users\gunar\.gemini\antigravity\scratch\rtl-cloud-api\cloudflared.exe" tunnel --url http://localhost:8000
