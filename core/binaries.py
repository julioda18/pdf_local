"""Localización y ejecución de programas externos (Tesseract, Ghostscript, LibreOffice).

Funciona en Windows, macOS y Linux: cada programa se identifica por un nombre
lógico y se busca en ``vendor/``, luego en el PATH y por último en rutas de app
conocidas del sistema.
"""

import os
import shutil
import subprocess
from functools import cache
from pathlib import Path

from .errors import ToolError

# PDF_LOCAL_VENDOR lo define la app de escritorio: vendor/ viaja junto al ejecutable.
VENDOR_DIR = Path(os.environ.get("PDF_LOCAL_VENDOR") or Path(__file__).resolve().parents[1] / "vendor")

# Patrones glob relativos a vendor/. Hoy solo el instalador de Windows usa vendor/;
# en macOS/Linux los programas vienen del gestor de paquetes y se encuentran por PATH.
VENDOR_PATTERNS = {
    "tesseract": ["Tesseract-OCR/tesseract.exe", "Tesseract-OCR/tesseract"],
    "ghostscript": ["gs/bin/gswin64c.exe", "gs/gs*/bin/gswin64c.exe"],
    "libreoffice": ["LibreOffice/program/soffice.exe", "LibreOffice/program/soffice"],
}

# Ghostscript se llama gswin64c en Windows y gs en el resto.
COMMAND_NAMES = {
    "tesseract": ["tesseract"],
    "ghostscript": ["gswin64c", "gs"],
    "libreoffice": ["soffice", "libreoffice"],
}

# En macOS el cask de LibreOffice no añade soffice al PATH.
APP_PATHS = {
    "libreoffice": ["/Applications/LibreOffice.app/Contents/MacOS/soffice"],
}


@cache
def find_binary(name):
    """Devuelve la ruta del programa lógico ``name`` o ``None`` si no existe.

    Args:
        name: ``"tesseract"``, ``"ghostscript"`` o ``"libreoffice"``.

    El resultado se cachea durante la vida del proceso: si se instala un programa
    con el servidor encendido, hay que reiniciarlo para que lo detecte.
    """
    return _find_in_vendor(name) or _find_in_path(name) or _find_app(name)


def _find_in_vendor(name):
    """Ruta de mayor versión que encaje con los patrones de ``vendor/``."""
    # sorted + [-1] elige la versión más alta cuando el patrón admite varias (gs10.x, gs11.x).
    matches = sorted(m for pattern in VENDOR_PATTERNS.get(name, []) for m in VENDOR_DIR.glob(pattern))
    return matches[-1] if matches else None


def _find_in_path(name):
    """Primer nombre de comando de ``name`` que esté en el PATH."""
    found = next(filter(None, map(shutil.which, COMMAND_NAMES.get(name, []))), None)
    return Path(found) if found else None


def _find_app(name):
    """Primera ruta de aplicación conocida de ``name`` que exista."""
    return next((Path(p) for p in APP_PATHS.get(name, []) if Path(p).exists()), None)


def require_binary(name, product):
    """Como ``find_binary`` pero lanza ``ToolError`` nombrando ``product`` si falta."""
    path = find_binary(name)
    if path is None:
        raise ToolError(f"{product} no está instalado")
    return path


def env_with_binaries(*names):
    """Copia del entorno con las carpetas de ``names`` al inicio del PATH.

    Necesario cuando un programa invoca a otro por nombre (ocrmypdf llama a
    Tesseract y Ghostscript) y estos viven en ``vendor/`` fuera del PATH.
    """
    folders = [str(p.parent) for p in map(find_binary, names) if p]
    return {**os.environ, "PATH": os.pathsep.join([*folders, os.environ.get("PATH", "")])}


def run_command(args, timeout, env=None):
    """Ejecuta ``args`` y traduce timeouts o códigos de salida != 0 a ``ToolError``.

    Solo se expone la última línea de la salida de error: suele contener la causa
    y evita filtrar rutas o trazas largas al usuario.
    """
    try:
        subprocess.run(args, check=True, timeout=timeout, env=env, capture_output=True, text=True)
    except subprocess.TimeoutExpired:
        raise ToolError(f"El proceso tardó más de {timeout} s") from None
    except subprocess.CalledProcessError as error:
        detail = (error.stderr or error.stdout or "").strip().splitlines()[-1:] or ["sin detalle"]
        raise ToolError(f"Falló el proceso externo: {detail[0]}") from None
