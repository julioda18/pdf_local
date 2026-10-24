@echo off
rem Crea .venv e instala Tesseract, Ghostscript y LibreOffice en vendor\ (Windows).
cd /d %~dp0
python scripts\install_vendor.py
pause
