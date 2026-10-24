"""Registro de herramientas expuestas en ``/api/<nombre>``.

Contrato de cada herramienta::

    def herramienta(inputs: list[Path], out: Path, **opciones: str) -> Path

- ``inputs``: archivos subidos, ya validados y en el orden en que se subieron.
- ``out``: ruta sugerida para el resultado dentro de la carpeta temporal.
- ``opciones``: campos del formulario (siempre texto); los no usados se ignoran con ``**_``.
- Devuelve la ruta real del resultado (puede ser ``.zip`` u otro nombre).
- Ante entradas inválidas lanza ``ToolError``.

Para añadir una herramienta: escribir la función en el módulo temático que
corresponda, registrarla aquí y añadir su tarjeta en ``static/app.js``.
"""

from dataclasses import dataclass
from typing import Callable

from . import export, external, images, optimize, pages, security, stamps


@dataclass(frozen=True)
class Tool:
    """Herramienta registrada.

    Attributes:
        run: Función que cumple el contrato descrito en este módulo.
        accepts: Clave de ``core.uploads.EXTENSIONS`` con los tipos aceptados.
        is_available: Indica si sus dependencias externas están instaladas.
    """

    run: Callable
    accepts: str = "pdf"
    is_available: Callable[[], bool] = lambda: True


TOOLS = {
    "merge": Tool(pages.merge),
    "split": Tool(pages.split),
    "organize": Tool(pages.organize),
    "rotate": Tool(pages.rotate),
    "compress": Tool(optimize.compress),
    "pdf_to_img": Tool(images.pdf_to_images),
    "img_to_pdf": Tool(images.images_to_pdf, accepts="image"),
    "pdf_to_word": Tool(export.pdf_to_word, is_available=export.word_available),
    "pdf_to_excel": Tool(export.pdf_to_excel, is_available=export.excel_available),
    "pdf_to_ppt": Tool(export.pdf_to_ppt, is_available=export.ppt_available),
    "protect": Tool(security.protect),
    "unlock": Tool(security.unlock),
    "watermark": Tool(stamps.watermark),
    "page_numbers": Tool(stamps.page_numbers),
    "ocr": Tool(external.ocr, is_available=external.ocr_available),
    "office_to_pdf": Tool(external.office_to_pdf, accepts="office", is_available=external.office_available),
}
