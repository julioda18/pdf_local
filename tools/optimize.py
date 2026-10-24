"""Compresión de PDF."""

from core.params import choice
from core.pdf_io import open_pdf

# nivel -> (dpi objetivo de imágenes, calidad JPEG 0-100)
COMPRESSION_LEVELS = {"baja": (150, 85), "media": (110, 65), "alta": (72, 45)}
# Margen para no recomprimir imágenes que ya están apenas por encima del objetivo.
DPI_TOLERANCE = 10
# garbage=4 además fusiona streams idénticos; es más lento pero aquí el tamaño es el objetivo.
MAX_GARBAGE_LEVEL = 4


def compress(inputs, out, level="media", **_):
    """Reduce el tamaño del PDF.

    Baja la resolución y calidad de las imágenes, deja en las fuentes solo los
    glifos usados y limpia objetos redundantes.

    Args:
        level: ``"baja"``, ``"media"`` o ``"alta"`` (más compresión = menos calidad).
    """
    target_dpi, jpeg_quality = COMPRESSION_LEVELS[choice(level, "Nivel", COMPRESSION_LEVELS)]
    with open_pdf(inputs[0]) as doc:
        doc.rewrite_images(dpi_threshold=target_dpi + DPI_TOLERANCE, dpi_target=target_dpi, quality=jpeg_quality)
        doc.subset_fonts()
        doc.save(out, garbage=MAX_GARBAGE_LEVEL, deflate=True, clean=True)
    return out
