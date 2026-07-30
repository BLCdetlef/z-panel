@echo off
cd /d "%~dp0"
py -3 news_studio_5_24_4.py
if errorlevel 1 (
  echo.
  echo News Studio 5.24.4 konnte nicht gestartet werden.
  echo Siehe news_studio_5_24_4_startfehler.txt
  pause
)
