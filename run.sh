#!/usr/bin/env sh
# Arranca PDF Local en macOS/Linux; crea .venv la primera vez.
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi
URL=http://127.0.0.1:5000
(sleep 2; command -v open >/dev/null && open "$URL" || xdg-open "$URL" >/dev/null 2>&1 || true) &
.venv/bin/python app.py
