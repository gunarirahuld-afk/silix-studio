@echo off
title Stop SILIX Studio
echo Stopping all SILIX processes...
taskkill /f /im cloudflared.exe >nul 2>&1
taskkill /f /im uvicorn.exe >nul 2>&1
echo [OK] SILIX has been completely stopped.
timeout /t 2 /nobreak >nul
