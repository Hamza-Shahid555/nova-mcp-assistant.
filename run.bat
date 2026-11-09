@echo off
REM One-click setup + launch on Windows.
cd /d %~dp0
if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
    call .venv\Scripts\activate
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate
)
if not exist .env copy .env.example .env
python -m app.seed
streamlit run app\main.py
