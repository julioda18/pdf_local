"""Apertura, guardado y empaquetado de PDF compartidos por todas las herramientas."""

import zipfile

import pymupdf

from .errors import ToolError

# garbage=3 elimina objetos huérfanos y duplicados; deflate comprime los streams.
SAVE_OPTIONS = {"garbage": 3, "deflate": True}


def open_pdf(path, data=None):
    """Abre un PDF con PyMuPDF validando que sea legible y no esté cifrado.

    Args:
        path: Ruta del PDF; con ``data`` solo se usa su nombre en los mensajes.
        data: Contenido ya leído, para abrirlo desde memoria sin tocar disco.

    Raises:
        ToolError: Si el archivo está dañado o requiere contraseña.
    """
    try:
        doc = pymupdf.open(path) if data is None else pymupdf.open("pdf", data)
    except pymupdf.FileDataError:
        raise ToolError(f"PDF dañado o ilegible: {path.name}") from None
    if doc.needs_pass:
        raise ToolError(f"{path.name} tiene contraseña: usa 'Desbloquear PDF' primero")
    return doc


def release_cache():
    """Vacía la caché global de recursos de MuPDF (fuentes, imágenes decodificadas).

    No tiene límite por defecto y sobrevive al cierre de los documentos: sin esto
    el servidor crece ~35 MB por operación en PDF con imágenes y nunca los devuelve.
    """
    pymupdf.TOOLS.store_shrink(100)


def save_pdf(doc, out):
    """Guarda ``doc`` en ``out`` con las opciones estándar y devuelve la ruta."""
    doc.save(out, **SAVE_OPTIONS)
    return out


def pdf_bytes(doc):
    """Serializa ``doc`` en memoria (para meterlo en un ZIP sin tocar disco)."""
    return doc.tobytes(**SAVE_OPTIONS)


def write_zip(out, entries):
    """Crea un ZIP junto a ``out`` (misma ruta, extensión ``.zip``).

    Args:
        out: Ruta de salida sugerida por la petición.
        entries: Iterable de tuplas ``(nombre_en_zip, bytes)``. Puede ser un
            generador: se consume de uno en uno para no cargar todo en memoria.

    Returns:
        Ruta del ZIP creado.
    """
    zip_path = out.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries:
            archive.writestr(name, data)
    return zip_path
