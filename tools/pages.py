"""Herramientas que reorganizan páginas: unir, dividir, reordenar y rotar."""

import pymupdf

from core.params import as_int, parse_page_groups, parse_page_ranges
from core.pdf_io import open_pdf, pdf_bytes, save_pdf, write_zip

RIGHT_ANGLES = {90, 180, 270}
FULL_TURN = 360


def merge(inputs, out, **_):
    """Concatena todos los PDF de ``inputs`` en el orden recibido."""
    merged = pymupdf.open()
    for path in inputs:
        with open_pdf(path) as source:
            merged.insert_pdf(source)
    return save_pdf(merged, out)


def split(inputs, out, ranges="", **_):
    """Divide el PDF en varios archivos empaquetados en un ZIP.

    Args:
        ranges: Grupos separados por ``;`` (``"1-3;4-6"``). Vacío = una página por archivo.
    """
    with open_pdf(inputs[0]) as source:
        groups = parse_page_groups(ranges, source.page_count)
        parts = ((f"parte_{n}.pdf", pdf_bytes(_extract(source, pages))) for n, pages in enumerate(groups, 1))
        return write_zip(out, parts)


def organize(inputs, out, order="", **_):
    """Deja solo las páginas de ``order`` y en ese orden (sirve para reordenar y eliminar).

    Args:
        order: Rangos como ``"3,1,2,5-8"``; las páginas omitidas se eliminan.
    """
    with open_pdf(inputs[0]) as doc:
        doc.select(parse_page_ranges(order, doc.page_count))
        return save_pdf(doc, out)


def rotate(inputs, out, angle="90", pages="", **_):
    """Gira páginas en sentido horario sumando ``angle`` a su rotación actual.

    Args:
        angle: ``"90"``, ``"180"`` o ``"270"``.
        pages: Rangos a girar; vacío = todas.
    """
    degrees = as_int(angle, "Ángulo", RIGHT_ANGLES)
    with open_pdf(inputs[0]) as doc:
        targets = parse_page_ranges(pages, doc.page_count) if pages.strip() else range(doc.page_count)
        for index in targets:
            page = doc[index]
            page.set_rotation((page.rotation + degrees) % FULL_TURN)
        return save_pdf(doc, out)


def _extract(source, pages):
    """Nuevo documento con las páginas ``pages`` (índices base 0) de ``source``."""
    part = pymupdf.open()
    for index in pages:
        part.insert_pdf(source, from_page=index, to_page=index)
    return part
