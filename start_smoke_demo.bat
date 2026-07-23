@echo off
REM Open API + Dashboard in two windows (smoke demo)
set ROOT=%~dp0
start "ShopReview-API" cmd /k "%ROOT%backend\start.bat"
timeout /t 3 /nobreak >nul
start "ShopReview-Dashboard" cmd /k "%ROOT%dashboard\start.bat"
echo Started API and Dashboard windows.
echo Open http://127.0.0.1:5173 after Vite is ready.
pause
