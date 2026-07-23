@echo off
setlocal
cd /d "%~dp0\.."

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] .venv not found. Run:
  echo   python -m venv .venv
  echo   .venv\Scripts\python.exe -m pip install -r backend\requirements.txt
  exit /b 1
)

if not exist ".env" if exist "backend\.env.example" (
  copy /Y "backend\.env.example" ".env" >nul
)

set DATA_MODE=smoke
set SMOKE_EXPORT_DIR=exports/agent/smoke

echo ========================================
echo  ShopReview API  ^(Stage G smoke^)
echo  http://127.0.0.1:8080
echo  DATA_MODE=%DATA_MODE%
echo  SMOKE_EXPORT_DIR=%SMOKE_EXPORT_DIR%
echo  Order: start THIS first, then dashboard
echo ========================================

".venv\Scripts\python.exe" -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8080 --reload
set EXITCODE=%ERRORLEVEL%
echo.
echo API exited with code %EXITCODE%
pause
endlocal & exit /b %EXITCODE%
