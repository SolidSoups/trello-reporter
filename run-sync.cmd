@echo off
rem Fetch new reports from Discord now: label them and put them in a ## list or Incoming.
rem Same lock and data folder as the scheduled jobs, so it's safe to run alongside them.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo This PC is not set up yet. Run setup.cmd first.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" sync.py
pause
