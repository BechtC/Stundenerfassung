@echo off
REM Startet die Tray-App ohne Konsolenfenster (fuer Windows-Autostart).
cd /d "%~dp0"
start "" pythonw tray_timer.py
