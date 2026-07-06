@echo off
setlocal

cd /d "%~dp0backend"

if not exist ".venv\Scripts\python.exe" (
  echo Missing backend virtual environment at backend\.venv\Scripts\python.exe
  echo Create it first and install requirements:
  echo   cd backend
  echo   python -m venv .venv
  echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
  exit /b 1
)

.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8009
