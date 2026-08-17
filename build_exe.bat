@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt
pyinstaller --noconsole --name "ProtonVerteilerV3" --windowed --clean --distpath dist --workpath build src\main.py
if errorlevel 1 (
    echo.
    echo Build fehlgeschlagen.
    pause
)
