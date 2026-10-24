"""Validación de los parámetros que llegan del formulario web.

Todo valor del formulario llega como texto; estas funciones lo convierten al tipo
esperado o lanzan ``ToolError`` con un mensaje apto para mostrar al usuario.
"""

from .errors import ToolError

RANGE_SEPARATOR = ","
GROUP_SEPARATOR = ";"


def parse_page_ranges(spec, page_count):
    """Convierte una lista de rangos humanos en índices de página base 0.

    Args:
        spec: Texto como ``"1-3,5"``. Se respeta el orden y se permiten repeticiones.
        page_count: Total de páginas del documento, para validar los límites.

    Returns:
        Lista de índices, p. ej. ``[0, 1, 2, 4]``.

    Raises:
        ToolError: Si un rango es inválido, sale del documento o no hay ninguno.
    """
    indexes = []
    for part in filter(None, (p.strip() for p in spec.split(RANGE_SEPARATOR))):
        start, end = _parse_range(part)
        if not 1 <= start <= end <= page_count:
            raise ToolError(f"Rango fuera de 1-{page_count}: {part}")
        indexes.extend(range(start - 1, end))
    if not indexes:
        raise ToolError("Indica al menos una página")
    return indexes


def parse_page_groups(spec, page_count):
    """Convierte ``"1-2;3-5"`` en grupos de índices, uno por archivo de salida.

    Si ``spec`` está vacío, devuelve un grupo por página (dividir página a página).
    """
    groups = [g for g in spec.split(GROUP_SEPARATOR) if g.strip()]
    return [parse_page_ranges(g, page_count) for g in groups] or [[i] for i in range(page_count)]


def _parse_range(part):
    """``"3-5"`` -> ``(3, 5)``; ``"4"`` -> ``(4, 4)``."""
    first, _, last = part.partition("-")
    try:
        return int(first), int(last or first)
    except ValueError:
        raise ToolError(f"Rango inválido: {part}") from None


def as_int(value, name, allowed):
    """Convierte ``value`` a entero y exige que esté en el conjunto ``allowed``.

    ``name`` es la etiqueta que verá el usuario en el mensaje de error.
    """
    number = _to_number(int, value, name)
    if number not in allowed:
        raise ToolError(f"{name} debe ser uno de {sorted(allowed)}")
    return number


def as_float(value, name, low, high):
    """Convierte ``value`` a decimal y exige ``low <= valor <= high``."""
    number = _to_number(float, value, name)
    if not low <= number <= high:
        raise ToolError(f"{name} debe estar entre {low} y {high}")
    return number


def _to_number(convert, value, name):
    """Aplica ``convert`` (``int``/``float``) traduciendo el fallo a ``ToolError``."""
    try:
        return convert(value)
    except (TypeError, ValueError):
        raise ToolError(f"{name} debe ser un número") from None


def choice(value, name, options):
    """Devuelve ``value`` si pertenece a ``options``; si no, lanza ``ToolError``."""
    if value not in options:
        raise ToolError(f"{name} debe ser uno de {list(options)}")
    return value
