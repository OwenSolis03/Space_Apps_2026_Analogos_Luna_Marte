@echo off
rem Starts the PROTOTERRA website (Vite dev server) at http://localhost:5173
rem Double-click it, or run it from any terminal. Close the window to stop the server.
setlocal
cd /d "%~dp0app" || (echo App folder not found & pause & exit /b 1)

if not exist "node_modules\.bin\vite.cmd" (
  echo Installing dependencies ^(npm ci^)...
  call npm ci || (echo npm ci failed & pause & exit /b 1)
)

rem Free port 5173 if an old dev server is still holding it
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r /c:":5173 .*LISTENING"') do taskkill /f /pid %%p >nul 2>&1

start "" http://localhost:5173
call npm run dev -- --port 5173 --strictPort
pause
