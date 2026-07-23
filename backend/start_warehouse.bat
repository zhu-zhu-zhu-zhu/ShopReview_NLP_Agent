@echo off
setlocal
cd /d "%~dp0\.."

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] .venv not found. Run:
  echo   python -m venv .venv
  echo   .venv\Scripts\python.exe -m pip install -r backend\requirements.txt
  exit /b 1
)

if not exist "backend\.env" (
  echo [ERROR] backend\.env missing. Copy backend\.env.example and set MYSQL_* credentials.
  exit /b 1
)

REM Prefer connection values from ignored backend\.env.
set DATA_MODE=warehouse

echo ========================================
echo  ShopReview API  ^(warehouse / MySQL^)
echo  http://127.0.0.1:8080
echo  DATA_MODE=%DATA_MODE%
echo  Read-only user: agent_reader
echo ========================================

".venv\Scripts\python.exe" -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8080 --reload
set EXITCODE=%ERRORLEVEL%
echo.
echo API exited with code %EXITCODE%
pause
endlocal & exit /b %EXITCODE%
