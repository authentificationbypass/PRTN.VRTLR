@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt
python -m PyInstaller --noconsole --name "ProtonVerteilerV3" --windowed --icon "ico\PRTN.MV.ico" --clean --distpath dist --workpath build src\main.py
copy /Y "ico\PRTN.MV.ico" "dist\ProtonVerteilerV3\PRTN.MV.ico"
if errorlevel 1 (
    echo.
    echo Build fehlgeschlagen.
    pause
)
