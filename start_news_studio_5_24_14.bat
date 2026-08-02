@echo off
setlocal
cd /d "%~dp0"

title ZUSTAND News Studio 5.24.14

where py >nul 2>&1
if %errorlevel%==0 (
    py -3 news_studio_5_24_14.py
) else (
    python news_studio_5_24_14.py
)

if not %errorlevel%==0 (
    echo.
    echo News Studio 5.24.14 konnte nicht gestartet werden.
    echo Bitte pruefen Sie die Datei news_studio_5_24_14_startfehler.txt.
    echo.
    pause
)
endlocal
