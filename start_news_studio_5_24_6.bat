@echo off
cd /d "%~dp0"
py -3 news_studio_5_24_6.py
if errorlevel 1 (
  echo.
  echo News Studio 5.24.6 konnte nicht gestartet werden.
  echo Siehe news_studio_5_24_6_startfehler.txt
  pause
)
