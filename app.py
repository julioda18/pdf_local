"""Servidor web local de PDF Local.

Sirve la interfaz (``static/``) y expone cada herramienta en ``POST /api/<nombre>``.
Escucha solo en 127.0.0.1: ningún otro equipo de la red puede conectarse.
"""

import tempfile
from io import BytesIO
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_file
from werkzeug.exceptions import RequestEntityTooLarge

from core.errors import ToolError
from core.uploads import save_uploads
from tools import TOOLS
from tools.preview import PreviewStore

HOST = "127.0.0.1"
PORT = 5000
MAX_UPLOAD_MB = 500
BAD_REQUEST = 400
PAYLOAD_TOO_LARGE = 413
PREVIEW_CACHE_SECONDS = 3600

app = Flask(__name__, static_folder="static", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024
previews = PreviewStore()


@app.get("/")
def index():
    """Página principal con la cuadrícula de herramientas."""
    return app.send_static_file("index.html")


@app.get("/api/tools")
def tools_status():
    """``{nombre: disponible}`` para que la interfaz desactive las herramientas sin dependencias."""
    return jsonify({name: tool.is_available() for name, tool in TOOLS.items()})


@app.post("/api/preview")
def preview_upload():
    """Registra el primer PDF de ``files`` para previsualizarlo.

    Returns:
        ``{"id": token, "ratios": [alto/ancho, ...]}``; las proporciones permiten
        reservar el hueco de cada miniatura antes de que cargue.
    """
    with tempfile.TemporaryDirectory() as folder:
        inputs = save_uploads(request.files.getlist("files"), "pdf", Path(folder))
        token, ratios = previews.add(inputs[0])
    return jsonify(id=token, ratios=ratios)


@app.get("/api/preview/<token>/<int:number>")
def preview_page(token, number):
    """Miniatura de una página; el navegador la guarda en caché mientras dure la sesión."""
    data, mimetype = previews.thumbnail(token, number)
    response = send_file(BytesIO(data), mimetype=mimetype)
    response.headers["Cache-Control"] = f"private, max-age={PREVIEW_CACHE_SECONDS}, immutable"
    return response


@app.post("/api/<name>")
def process(name):
    """Ejecuta la herramienta ``name`` sobre los archivos del campo ``files``.

    El resto de campos del formulario se pasan como opciones a la herramienta.
    Todo ocurre en una carpeta temporal que se borra antes de responder.

    Returns:
        El archivo resultante como descarga, o JSON ``{"error": ...}`` con 400.
    """
    tool = TOOLS.get(name) or abort(404)
    with tempfile.TemporaryDirectory() as folder:
        workdir = Path(folder)
        inputs = save_uploads(request.files.getlist("files"), tool.accepts, workdir)
        result = Path(tool.run(inputs, workdir / "resultado.pdf", **request.form.to_dict()))
        # Se copia a memoria para poder borrar la carpeta temporal antes de responder.
        payload = BytesIO(result.read_bytes())
    return send_file(payload, as_attachment=True, download_name=f"{name}{result.suffix}")


@app.errorhandler(ToolError)
def tool_error(error):
    """Devuelve los errores esperados como JSON que la interfaz muestra al usuario."""
    return jsonify(error=str(error)), BAD_REQUEST


@app.errorhandler(RequestEntityTooLarge)
def too_large(_error):
    """Responde en JSON (no en HTML) cuando la subida supera ``MAX_UPLOAD_MB``."""
    return jsonify(error=f"Los archivos superan {MAX_UPLOAD_MB} MB"), PAYLOAD_TOO_LARGE


if __name__ == "__main__":
    app.run(host=HOST, port=PORT)
