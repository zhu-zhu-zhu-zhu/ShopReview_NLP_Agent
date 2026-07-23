@echo off
setlocal
cd /d "%~dp0"

where npm.cmd >nul 2>&1
if errorlevel 1 (
  echo [ERROR] npm.cmd not found. Install Node.js, then retry.
  exit /b 1
)

if not exist "node_modules" (
  echo Installing dependencies with npm.cmd ...
  call npm.cmd install
  if errorlevel 1 exit /b 1
)

if not exist ".env" if exist ".env.example" (
  copy /Y ".env.example" ".env" >nul
)

echo ========================================
echo  ShopReview Dashboard  ^(Stage G smoke^)
echo  http://127.0.0.1:5173
echo  Requires API: http://127.0.0.1:8080
echo  Start backend\start.bat FIRST
echo ========================================

call npm.cmd run dev -- --host 127.0.0.1 --port 5173
set EXITCODE=%ERRORLEVEL%
echo.
echo Dashboard exited with code %EXITCODE%
pause
endlocal & exit /b %EXITCODE%
