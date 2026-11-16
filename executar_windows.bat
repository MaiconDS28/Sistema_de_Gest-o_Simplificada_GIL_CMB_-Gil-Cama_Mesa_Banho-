@echo off
chcp 65001 >nul
echo ====================================================================
echo   INICIANDO SISTEMA DE GESTAO SIMPLIFICADA - GIL CMB (PYTHON/FLASK)
echo ====================================================================
if not exist venv (
    python -m venv venv
)
call venv\Scripts\activate
pip install -r requirements.txt --quiet
start http://127.0.0.1:5000
python app.py
pause
