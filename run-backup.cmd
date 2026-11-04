@echo off
rem Save a snapshot of the board now.
rem Same lock and data folder as the scheduled jobs, so it's safe to run alongside them.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo This PC is not set up yet. Run setup.cmd first.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" backup.py --note manual
pause
