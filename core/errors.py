"""Excepción común a todo el proyecto."""


class ToolError(Exception):
    """Error esperado (entrada inválida o programa externo ausente).

    Su mensaje se devuelve tal cual al usuario con HTTP 400, por eso debe estar
    redactado en español claro y no contener rutas internas ni trazas.
    Los errores inesperados NO deben envolverse en ``ToolError``: así llegan como
    500 y quedan visibles en la consola para depurarlos.
    """
