@echo off
cd /d "%~dp0"
py -3 news_studio_5_24_13.py
if errorlevel 1 (
  echo.
  echo News Studio 5.24.13 konnte nicht gestartet werden.
  echo Siehe news_studio_5_24_13_startfehler.txt
  pause
)
