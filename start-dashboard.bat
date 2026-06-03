@echo off
title Stundenerfassung
cd /d "%~dp0"
start "" "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" "http://localhost:8502"
streamlit run app.py --server.headless true --server.port 8502
