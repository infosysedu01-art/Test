@echo off
REM Start the attendance server (Windows).  Edit the lines below if needed.
cd /d "%~dp0"
REM set DATABASE_URL=mysql+pymysql://user:password@dbserver/lion_attendance
REM set HTTPS=1
python serve.py
pause
