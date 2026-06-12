@echo off
REM SPS SecureDesk AI - one-click start (Windows)
cd /d "%~dp0"
pip install -r requirements.txt -q
python -m uvicorn app.main:app --port 8000
