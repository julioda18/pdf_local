#!/usr/bin/env sh
# Crea .venv e instala Tesseract, Ghostscript y LibreOffice (macOS: Homebrew, Linux: apt/dnf/pacman/zypper).
set -e
cd "$(dirname "$0")"
python3 scripts/install_vendor.py
