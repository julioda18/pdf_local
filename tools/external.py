"""Herramientas que dependen de programas externos instalados en ``vendor/``."""

import sys

from core.binaries import env_with_binaries, find_binary, require_binary, run_command
from core.errors import ToolError
from core.params import choice

OCR_LANGUAGES = ("spa", "eng", "spa+eng")
OCR_TIMEOUT_SECONDS = 600
OFFICE_TIMEOUT_SECONDS = 180


def ocr_available():
    """``True`` si están Tesseract y Ghostscript (ocrmypdf necesita ambos)."""
    return all(find_binary(name) for name in ("tesseract", "ghostscript"))


def office_available():
    """``True`` si está LibreOffice."""
    return find_binary("libreoffice") is not None


def ocr(inputs, out, lang="spa", **_):
    """Añade una capa de texto buscable a un PDF escaneado.

    Las páginas que ya tienen texto se dejan intactas (``--skip-text``).

    Args:
        lang: Código de idioma de Tesseract: ``"spa"``, ``"eng"`` o ``"spa+eng"``.
    """
    language = choice(lang, "Idioma", OCR_LANGUAGES)
    require_binary("tesseract", "Tesseract OCR")
    require_binary("ghostscript", "Ghostscript")
    # Se usa el ocrmypdf del mismo intérprete (.venv) para no depender de un ocrmypdf global.
    args = [sys.executable, "-m", "ocrmypdf", "-l", language, "--skip-text", str(inputs[0]), str(out)]
    run_command(args, OCR_TIMEOUT_SECONDS, env_with_binaries("tesseract", "ghostscript"))
    return out


def office_to_pdf(inputs, out, **_):
    """Convierte un documento de Office/OpenDocument/texto a PDF con LibreOffice.

    LibreOffice decide el nombre de salida (``<nombre original>.pdf`` en ``out.parent``),
    por eso se devuelve esa ruta y no ``out``.
    """
    soffice = require_binary("libreoffice", "LibreOffice")
    source = inputs[0]
    run_command([str(soffice), "--headless", "--convert-to", "pdf", "--outdir", str(out.parent), str(source)],
                OFFICE_TIMEOUT_SECONDS)
    result = out.parent / f"{source.stem}.pdf"
    if not result.exists():
        raise ToolError(f"LibreOffice no pudo convertir {source.name}")
    return result
