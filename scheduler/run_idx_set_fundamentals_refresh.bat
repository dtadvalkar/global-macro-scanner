@echo off
REM Wrapper for Windows Task Scheduler to invoke the monthly IDX/SET
REM yahooquery fundamentals refresh.
REM
REM Calls scripts/etl/yahooquery/schedule_monthly_idx_set_fundamentals.py
REM with no flags so the script's own due rule (1st of month OR > 25 days
REM since last refresh) governs whether the seeder actually executes.
REM
REM Task Scheduler setup is documented in
REM docs/tasks/idx_set_operations_hardening_progress.md.
REM
REM Exit code propagates from the Python wrapper:
REM   0  not due (skipped) or due/forced run succeeded
REM   nonzero  seeder subprocess failed

setlocal
set REPO_ROOT=%~dp0..
cd /d "%REPO_ROOT%"
set PYTHON=%REPO_ROOT%\.venv\Scripts\python.exe
if not exist "%PYTHON%" (
    echo [err] Python interpreter not found at "%PYTHON%"
    exit /b 1
)
"%PYTHON%" "%REPO_ROOT%\scripts\etl\yahooquery\schedule_monthly_idx_set_fundamentals.py"
set RC=%ERRORLEVEL%
endlocal & exit /b %RC%
