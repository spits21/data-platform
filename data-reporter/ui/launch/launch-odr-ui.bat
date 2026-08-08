@echo off
REM Double-click launcher for the ODR chat UI (Windows, non-technical users).
cd /d "%~dp0..\.."
echo Starting Ops Data Reporter chat UI...
uv run odr ui
if errorlevel 1 (
    echo.
    echo Something went wrong starting the UI - see the message above.
    pause
)
