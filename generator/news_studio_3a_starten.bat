@echo off
cd /d "%~dp0.."
python generator\news_studio_3a.py
if errorlevel 1 (
  echo.
  echo ZUSTAND News Studio 3.0a konnte nicht gestartet werden.
  echo Bitte pruefen Sie, ob Python installiert ist.
  echo.
  pause
)
