"""Miniaturas de páginas bajo demanda para la interfaz de arrastrar y soltar.

El PDF se sube una sola vez (``PreviewStore.add``) y cada miniatura se pide por
separado, de modo que el navegador solo carga las páginas visibles en pantalla.
"""

import secrets
import threading
from collections import OrderedDict

import pymupdf

from core.errors import ToolError
from core.pdf_io import open_pdf

THUMB_WIDTH = 140
JPEG_QUALITY = 70
# Documentos recordados a la vez (en memoria); al superarlo se descarta el más antiguo.
MAX_DOCUMENTS = 4


class PreviewStore:
    """PDF previsualizados, abiertos en memoria e identificados por un token aleatorio.

    Se cargan desde memoria y no desde una copia en disco: escribir y reabrir un
    archivo nuevo dispara el análisis del antivirus y en Windows multiplica el
    tiempo de apertura. Los documentos quedan abiertos para reutilizar entre miniaturas lo que PyMuPDF ya
    decodificó (fuentes, imágenes). PyMuPDF no admite hilos concurrentes, así que el
    renderizado se serializa con un único lock; en equipos lentos esto además evita
    saturar la CPU con varias páginas a la vez.
    """

    def __init__(self, max_documents=MAX_DOCUMENTS):
        self._docs = OrderedDict()
        self._lock = threading.Lock()
        self._max = max_documents

    def add(self, path):
        """Carga ``path`` en memoria y devuelve ``(token, proporciones alto/ancho por página)``."""
        doc = open_pdf(path, path.read_bytes())
        ratios = [round(page.rect.height / page.rect.width, 3) for page in doc]
        token = secrets.token_urlsafe(16)
        with self._lock:
            self._docs[token] = doc
            while len(self._docs) > self._max:
                self._docs.popitem(last=False)[1].close()
        return token, ratios

    def thumbnail(self, token, number, width=THUMB_WIDTH):
        """Miniatura de la página ``number`` (base 1) como ``(bytes, mimetype)``.

        Raises:
            ToolError: Si el token caducó o la página no existe.
        """
        with self._lock:
            if token not in self._docs:
                raise ToolError("La vista previa caducó: vuelve a elegir el archivo")
            doc = self._docs[token]
            if not 1 <= number <= doc.page_count:
                raise ToolError(f"Página fuera de 1-{doc.page_count}")
            return render_page(doc[number - 1], width)


def render_page(page, width=THUMB_WIDTH):
    """Renderiza ``page`` a ``width`` px de ancho.

    Las páginas con imágenes (escaneos, fotos) van en JPEG, mucho más ligero para
    ese contenido; las de texto/vectoriales en PNG, que ahí pesa menos y no emborrona.
    """
    zoom = width / page.rect.width
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
    if page.get_images():
        return pix.tobytes("jpg", jpg_quality=JPEG_QUALITY), "image/jpeg"
    return pix.tobytes("png"), "image/png"
