@echo off
REM =====================================================
REM Juan365 Overdue Reminder Scheduler
REM Schedule this via Windows Task Scheduler to run hourly
REM =====================================================

echo [%date% %time%] Triggering overdue reminder check...

REM Call the API endpoint with secret token
curl -s "https://juan365-task-monitoring-production.up.railway.app/api/cron/overdue-reminders/?token=juan365-cron-secret-2024"

echo.
echo [%date% %time%] Done.
