@echo off
title Expedicao - NAO FECHE esta janela
set ENDERECO=https://localhost:8443
cd /d "%~dp0.."

echo Iniciando o sistema... Nao feche esta janela enquanto o site estiver em uso.
echo Para desligar o sistema, feche esta janela.
echo.

start "" /b "servidor\caddy.exe" run --config "servidor\Caddyfile"
start "" /b cmd /c "timeout /t 6 /nobreak >nul & start %ENDERECO%"
"venv\Scripts\python.exe" -m streamlit run app.py --server.headless true
