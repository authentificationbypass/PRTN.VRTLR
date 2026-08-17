@echo off
cd /d "%~dp0"
python -m src.main
if errorlevel 1 (
    echo.
    echo Fehler beim Starten der App.
    echo Bitte Python installieren und 'python -m pip install -r requirements.txt' ausfuehren.
    pause
)
