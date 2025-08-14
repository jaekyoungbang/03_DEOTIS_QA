@echo off
echo Installing docx2txt module...

REM Activate virtual environment
call venv_windows\Scripts\activate

REM Install docx2txt
pip install docx2txt==0.8

echo.
echo Installation complete!
echo Please restart the server.
pause