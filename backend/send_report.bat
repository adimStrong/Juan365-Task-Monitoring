@echo off
echo ================================================
echo   Creative Team Daily Report - Sending...
echo ================================================
echo.

cd /d "%~dp0"
python local_daily_report.py

echo.
pause
