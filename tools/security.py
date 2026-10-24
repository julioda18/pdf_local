"""Cifrado y descifrado de PDF con pikepdf (qpdf)."""

import pikepdf

from core.errors import ToolError

# R=6 es el algoritmo AES-256 del estándar PDF 2.0; el más fuerte disponible.
AES_256_REVISION = 6


def protect(inputs, out, password="", **_):
    """Cifra el PDF con AES-256; la misma contraseña sirve para abrir y editar.

    Raises:
        ToolError: Si la contraseña está vacía.
    """
    if not password:
        raise ToolError("Escribe una contraseña")
    encryption = pikepdf.Encryption(owner=password, user=password, R=AES_256_REVISION)
    with _open(inputs[0]) as pdf:
        pdf.save(out, encryption=encryption)
    return out


def unlock(inputs, out, password="", **_):
    """Guarda una copia sin cifrado. Requiere la contraseña actual del PDF."""
    with _open(inputs[0], password) as pdf:
        pdf.save(out)
    return out


def _open(path, password=""):
    """Abre con pikepdf traduciendo sus errores a ``ToolError``."""
    try:
        return pikepdf.open(path, password=password)
    except pikepdf.PasswordError:
        raise ToolError("Contraseña incorrecta o requerida") from None
    except pikepdf.PdfError:
        raise ToolError(f"PDF dañado o ilegible: {path.name}") from None
