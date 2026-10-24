"""Herramientas que estampan texto sobre las páginas: marca de agua y numeración."""

import pymupdf

from core.errors import ToolError
from core.params import as_float
from core.pdf_io import open_pdf, save_pdf

WATERMARK_GRAY = (0.6, 0.6, 0.6)
WATERMARK_ANGLE = -35
# Factor empírico: hace que el texto ocupe aprox. el ancho del lado corto de la página.
WATERMARK_WIDTH_RATIO = 1.4
# Punto de inicio del texto como fracción del ancho y alto de la página.
WATERMARK_ORIGIN = (0.15, 0.6)
FOOTER_HEIGHT = 20
FOOTER_MARGIN = 10
FOOTER_FONT_SIZE = 10


def watermark(inputs, out, text="CONFIDENCIAL", opacity="0.25", **_):
    """Estampa ``text`` en diagonal y semitransparente sobre cada página.

    Args:
        text: Texto de la marca (no vacío).
        opacity: Valor entre ``0`` (invisible) y ``1`` (opaco).
    """
    if not text.strip():
        raise ToolError("Escribe el texto de la marca de agua")
    alpha = as_float(opacity, "Opacidad", 0, 1)
    with open_pdf(inputs[0]) as doc:
        for page in doc:
            _stamp_diagonal(page, text, alpha)
        return save_pdf(doc, out)


def page_numbers(inputs, out, fmt="{n} / {total}", **_):
    """Añade un número centrado al pie de cada página.

    Args:
        fmt: Plantilla con ``{n}`` (página actual) y ``{total}``.
    """
    with open_pdf(inputs[0]) as doc:
        total = str(doc.page_count)
        for number, page in enumerate(doc, 1):
            # replace en lugar de str.format: el usuario controla fmt y format permitiría acceder a atributos.
            _stamp_footer(page, fmt.replace("{n}", str(number)).replace("{total}", total))
        return save_pdf(doc, out)


def _stamp_diagonal(page, text, alpha):
    """Dibuja ``text`` girado alrededor del centro de la página."""
    rect = page.rect
    center = pymupdf.Point(rect.width / 2, rect.height / 2)
    page.insert_text(
        pymupdf.Point(rect.width * WATERMARK_ORIGIN[0], rect.height * WATERMARK_ORIGIN[1]), text,
        fontsize=min(rect.width, rect.height) / len(text) * WATERMARK_WIDTH_RATIO,
        color=WATERMARK_GRAY, fill_opacity=alpha, stroke_opacity=alpha,
        morph=(center, pymupdf.Matrix(WATERMARK_ANGLE)),
    )


def _stamp_footer(page, label):
    """Escribe ``label`` centrado en una franja al pie de la página."""
    rect = page.rect
    box = pymupdf.Rect(0, rect.height - FOOTER_MARGIN - FOOTER_HEIGHT, rect.width, rect.height - FOOTER_MARGIN)
    page.insert_textbox(box, label, fontsize=FOOTER_FONT_SIZE, align=pymupdf.TEXT_ALIGN_CENTER)
