@echo off
cd /d "%~dp0"
start "" "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" --app=http://localhost:8502
timeout /t 2 /nobreak >nul
streamlit run app.py --server.headless true --server.port 8502
