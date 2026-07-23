@echo off
cd /d "%~dp0.."
python generator\news_studio_2.py
if errorlevel 1 (
  echo.
  echo ZUSTAND News Studio 2.0 konnte nicht gestartet werden.
  echo Bitte pruefen Sie, ob Python installiert ist.
  echo.
  pause
)
