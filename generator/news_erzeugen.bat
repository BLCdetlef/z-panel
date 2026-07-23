@echo off
cd /d "%~dp0.."
python generator\news_erzeugen.py
echo.
pause
