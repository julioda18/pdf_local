"""Validación y guardado de los archivos subidos desde el navegador."""

from werkzeug.utils import secure_filename

from .errors import ToolError

PDF_MAGIC = b"%PDF"
# La especificación PDF tolera basura antes de la cabecera, así que se busca en el primer KB.
MAGIC_SEARCH_BYTES = 1024

EXTENSIONS = {
    "pdf": {".pdf"},
    "image": {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".gif"},
    "office": {".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt", ".ods", ".odp", ".rtf", ".txt"},
}


def save_uploads(files, kind, folder):
    """Guarda los archivos subidos en ``folder`` y devuelve sus rutas en orden.

    Args:
        files: Lista de ``FileStorage`` de Flask.
        kind: Clave de ``EXTENSIONS`` que define qué tipos se aceptan.
        folder: Carpeta temporal de la petición.

    Raises:
        ToolError: Si no hay archivos o alguno no es del tipo esperado.
    """
    if not files:
        raise ToolError("No se recibieron archivos")
    # El prefijo numérico conserva el orden de subida y evita choques entre nombres iguales.
    return [_save_upload(f, kind, folder / f"{i:03d}_{secure_filename(f.filename) or 'archivo'}")
            for i, f in enumerate(files)]


def _save_upload(file, kind, path):
    """Valida la extensión, guarda el archivo y, si es PDF, comprueba su cabecera."""
    if path.suffix.lower() not in EXTENSIONS[kind]:
        raise ToolError(f"Tipo de archivo no permitido: {file.filename}")
    file.save(path)
    if kind == "pdf" and PDF_MAGIC not in path.read_bytes()[:MAGIC_SEARCH_BYTES]:
        raise ToolError(f"No es un PDF válido: {file.filename}")
    return path
