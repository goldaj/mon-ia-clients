@echo off
cd /d %~dp0
if not exist .venv (
  py -3.11 -m venv .venv
)
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements-build.txt
pyinstaller --noconfirm --clean --onefile --windowed --name MonIA app.py
echo.
echo EXE cree dans dist\MonIA.exe
pause
