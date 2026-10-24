"""Conversión entre PDF e imágenes."""

import pymupdf

from core.errors import ToolError
from core.params import as_int, choice
from core.pdf_io import open_pdf, save_pdf, write_zip

IMAGE_FORMATS = ("jpg", "png")
DPI_OPTIONS = {72, 150, 300}


def pdf_to_images(inputs, out, fmt="jpg", dpi="150", **_):
    """Renderiza cada página como imagen y las devuelve en un ZIP.

    Args:
        fmt: ``"jpg"`` (ligero) o ``"png"`` (sin pérdida).
        dpi: ``"72"``, ``"150"`` o ``"300"``.
    """
    image_format = choice(fmt, "Formato", IMAGE_FORMATS)
    resolution = as_int(dpi, "DPI", DPI_OPTIONS)
    with open_pdf(inputs[0]) as doc:
        images = ((f"pagina_{n}.{image_format}", page.get_pixmap(dpi=resolution).tobytes(image_format))
                  for n, page in enumerate(doc, 1))
        return write_zip(out, images)


def images_to_pdf(inputs, out, **_):
    """Crea un PDF con una página por imagen, en el orden recibido."""
    result = pymupdf.open()
    for path in inputs:
        result.insert_pdf(_image_as_pdf(path))
    return save_pdf(result, out)


def _image_as_pdf(path):
    """Convierte una imagen en un PDF de una página del mismo tamaño."""
    try:
        with pymupdf.open(path) as image:
            return pymupdf.open("pdf", image.convert_to_pdf())
    except (pymupdf.FileDataError, RuntimeError):
        raise ToolError(f"Imagen ilegible: {path.name}") from None
