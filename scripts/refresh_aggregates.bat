@echo off
cd /d C:\Users\us\Projects\ticketing-system\scripts
python refresh_aggregates_prod.py >> refresh_aggregates.log 2>&1
