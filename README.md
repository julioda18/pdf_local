# PDF Local

Herramientas PDF al estilo iLovePDF que se ejecutan **solo en tu equipo**. Ningún archivo sale a internet: el servidor escucha únicamente en `127.0.0.1`, la interfaz no carga recursos externos y cada archivo se borra al terminar la petición.

---

## Índice

1. [Herramientas](#herramientas)
2. [Requisitos](#requisitos)
3. [Instalación](#instalación)
4. [Uso](#uso)
5. [Privacidad y seguridad](#privacidad-y-seguridad)
6. [Arquitectura](#arquitectura)
7. [API](#api)
8. [Añadir una herramienta](#añadir-una-herramienta)
9. [Pruebas](#pruebas)
10. [Solución de problemas](#solución-de-problemas)

---

## Herramientas

| Herramienta | Qué hace | Opciones | Salida |
|---|---|---|---|
| Unir PDF | Concatena varios PDF en el orden subido | — | `.pdf` |
| Dividir PDF | Separa en varios archivos | Grupos `1-3;4-6` (vacío = una página por archivo) | `.zip` |
| Organizar páginas | Reordena y elimina páginas | Orden `3,1,2,5-8` (las omitidas se eliminan) | `.pdf` |
| Rotar PDF | Gira en sentido horario | Ángulo 90/180/270, páginas (vacío = todas) | `.pdf` |
| Comprimir PDF | Reduce imágenes, fuentes y objetos sobrantes | Nivel baja/media/alta | `.pdf` |
| PDF a imagen | Una imagen por página | JPG/PNG, 72/150/300 DPI | `.zip` |
| Imagen a PDF | Una página por imagen | — | `.pdf` |
| Proteger PDF | Cifrado AES-256 | Contraseña | `.pdf` |
| Desbloquear PDF | Quita la contraseña | Contraseña actual | `.pdf` |
| Marca de agua | Texto diagonal semitransparente | Texto, opacidad 0–1 | `.pdf` |
| Numerar páginas | Número centrado al pie | Formato con `{n}` y `{total}` | `.pdf` |
| OCR | Hace buscable un PDF escaneado | Idioma spa/eng/spa+eng | `.pdf` |
| Office a PDF | Word, Excel, PowerPoint, ODT/ODS/ODP, RTF, TXT | — | `.pdf` |

Formato de rangos: páginas empezando en 1, separadas por coma; `a-b` es un intervalo. En *Dividir* cada grupo separado por `;` produce un archivo.

---

## Requisitos

| Componente | Para qué | Windows | macOS | Linux |
|---|---|---|---|---|
| Python 3.11+ | Servidor y herramientas | sistema | sistema | sistema |
| Flask, PyMuPDF, pikepdf, ocrmypdf | Librerías | `.venv\` | `.venv/` | `.venv/` |
| Tesseract OCR (+ `spa`) | OCR | `vendor\Tesseract-OCR\` | Homebrew | paquete del sistema |
| Ghostscript | OCR (lo usa ocrmypdf) | `vendor\gs\` | Homebrew | paquete del sistema |
| LibreOffice | Office a PDF | `vendor\LibreOffice\` | `/Applications` (cask) | paquete del sistema |

`core/binaries.py` busca cada programa primero en `vendor/`, luego en el PATH y, por último, en rutas de aplicación conocidas (por ejemplo LibreOffice.app en macOS). Si falta alguno, la herramienta que lo necesita aparece desactivada y las demás siguen funcionando.

---

## Instalación

Un solo comando deja todo listo: crea el entorno virtual `.venv`, instala las librerías de `requirements.txt` y luego los programas externos.

| Sistema | Comando | Programas externos |
|---|---|---|
| Windows | `install_vendor.bat` | winget + instaladores oficiales; todo dentro de `vendor\` |
| macOS | `./install_vendor.sh` | `brew install tesseract tesseract-lang ghostscript` y `brew install --cask libreoffice` |
| Linux | `./install_vendor.sh` | apt / dnf / pacman / zypper con `sudo` |

Ambos llaman a [scripts/install_vendor.py](scripts/install_vendor.py), que:

- solo usa la biblioteca estándar de Python, así que funciona antes de que exista el `.venv`;
- crea `.venv` si falta y siempre ejecuta `pip install -r requirements.txt`, así se aplican los cambios en las dependencias;
- es idempotente: omite los programas que ya están instalados;
- al final muestra la ruta del venv y de cada programa, y termina con código 1 si algo sigue faltando.

Los programas externos solo hacen falta para OCR y Office. Sin ellos, el resto de herramientas funciona.

**Particularidades de Windows**

- Pide permisos de administrador (UAC) para Ghostscript y Tesseract.
- El instalador de Tesseract ignora la ruta elegida y se instala en `C:\Program Files`. Como el programa es portable, el script lo copia a `vendor\` y desinstala la copia de C:.
- Descarga `spa.traineddata` (español), que no viene en el instalador de Windows.
- Ghostscript no está en winget, así que se descarga la última versión desde su [GitHub oficial](https://github.com/ArtifexSoftware/ghostpdl-downloads/releases).

`run.bat` y `run.sh` también crean el `.venv` si no existe, por si arrancas sin pasar antes por el instalador.

---

## Uso

1. Windows: doble clic en `run.bat`. macOS/Linux: `./run.sh` (la primera vez, `chmod +x run.sh install_vendor.sh`).
2. Se abre `http://127.0.0.1:5000`.
3. Elige una herramienta, arrastra los archivos, ajusta las opciones y pulsa **Procesar**.
4. El resultado se descarga automáticamente.

Para detener el servidor, pulsa `Ctrl+C` o cierra la consola.

---

## Privacidad y seguridad

- **Sin red**: el servidor solo acepta conexiones de este equipo (`127.0.0.1`). La interfaz no usa CDN, fuentes ni analíticas externas.
- **Sin rastro en disco**: cada petición trabaja en una carpeta temporal propia (`tempfile.TemporaryDirectory`) que se borra antes de enviar la respuesta.
- **Validación de entrada**: lista blanca de extensiones por herramienta, comprobación de la cabecera `%PDF`, nombres saneados con `secure_filename`, y un límite de 500 MB por petición.
- **Parámetros validados**: los rangos, ángulos, DPI y niveles se comprueban antes de procesar. La plantilla de numeración usa `replace` y no `str.format`, para que no se pueda acceder a atributos internos.
- **Procesos externos acotados**: tiempo límite (OCR 600 s, Office 180 s), sin `shell=True`, y solo la última línea del error llega al usuario.
- **Cifrado**: *Proteger PDF* usa AES-256 (revisión 6 del estándar PDF 2.0).

> Las contraseñas se envían al servidor local en el formulario, pero nunca se guardan ni se registran.

---

## Arquitectura

```
pdf_local/
├── app.py               Servidor Flask: rutas y manejo de errores
├── core/                Utilidades compartidas (sin lógica de herramientas)
│   ├── errors.py        ToolError: error esperado → HTTP 400 con mensaje para el usuario
│   ├── params.py        Validación de opciones: rangos, enteros, decimales, listas
│   ├── pdf_io.py        Abrir/guardar PDF y crear ZIP
│   ├── uploads.py       Validación y guardado de subidas
│   └── binaries.py      Localizar y ejecutar programas de vendor/
├── tools/               Una función por herramienta, agrupadas por tema
│   ├── __init__.py      Registro TOOLS y contrato común
│   ├── pages.py         merge, split, organize, rotate
│   ├── optimize.py      compress
│   ├── images.py        pdf_to_images, images_to_pdf
│   ├── security.py      protect, unlock
│   ├── stamps.py        watermark, page_numbers
│   └── external.py      ocr, office_to_pdf
├── static/              index.html + app.js (sin dependencias externas)
├── tests/               pytest
├── scripts/
│   └── install_vendor.py  Instalador multiplataforma de programas externos
├── vendor/              Tesseract, Ghostscript, LibreOffice en Windows (ignorado por git)
├── install_vendor.bat / install_vendor.sh
├── run.bat / run.sh
└── requirements.txt
```

**Flujo de una petición**

```
navegador ─POST /api/<tool>─▶ app.process
   └─ save_uploads (valida y guarda en carpeta temporal)
   └─ TOOLS[tool].run(inputs, out, **opciones)
         └─ core.params valida opciones → pymupdf / pikepdf / programa externo
   └─ lee el resultado a memoria → borra la carpeta temporal → descarga
   └─ ToolError → 400 {"error": "..."}
```

**Decisiones de diseño**

- *Errores*: solo `ToolError` se muestra al usuario. Un error inesperado llega como 500 y deja la traza en la consola para depurarlo.
- *Librerías*: PyMuPDF hace casi todo; pikepdf (qpdf) se encarga del cifrado; ocrmypdf orquesta Tesseract y Ghostscript.
- *Binarios*: cada programa tiene un nombre lógico (`tesseract`, `ghostscript`, `libreoffice`). `core.binaries.find_binary` lo busca en `vendor/`, luego en el PATH (`gswin64c` o `gs`, `soffice` o `libreoffice`) y después en rutas de aplicación conocidas. Guarda el resultado en caché, así que hay que reiniciar el servidor tras instalar un programa.

---

## API

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/tools` | `{"merge": true, "ocr": false, ...}`: disponibilidad de cada herramienta |
| `POST` | `/api/<tool>` | `multipart/form-data` con uno o más `files` y las opciones como campos |

Respuestas de `POST`: `200` con el archivo como descarga, `400` y `{"error": "..."}` si la entrada no es válida, `404` si la herramienta no existe, `413` si se supera el límite de tamaño.

Ejemplo con curl:

```bash
curl -F files=@a.pdf -F files=@b.pdf -o unido.pdf http://127.0.0.1:5000/api/merge
```

```bash
curl -F files=@doc.pdf -F angle=90 -F pages=1-2 -o rotado.pdf http://127.0.0.1:5000/api/rotate
```

---

## Añadir una herramienta

1. Escribe la función en el módulo de `tools/` que corresponda (o crea uno nuevo si es otra temática):

   ```python
   def grayscale(inputs, out, **_):
       """Convierte todas las páginas a escala de grises."""
       with open_pdf(inputs[0]) as doc:
           ...
           return save_pdf(doc, out)
   ```

   Contrato: recibe `inputs: list[Path]`, `out: Path` y las opciones como texto; devuelve la ruta del resultado; lanza `ToolError` si la entrada no es válida. Usa `core.params` para validar las opciones.

2. Regístrala en `tools/__init__.py`: `"grayscale": Tool(stamps.grayscale)`. Añade `accepts=` o `is_available=` si la herramienta los necesita.
3. Añade su tarjeta en `TOOLS` de `static/app.js` con la misma clave.
4. Añade un test en `tests/test_tools.py`.

---

## Pruebas

```bash
.venv\Scripts\python -m pytest -q tests
```

Cubren cada herramienta (incluidos los casos de error), el análisis de rangos y la API (subida de un PDF falso, unión de dos PDF). Los tests de OCR y Office se marcan como *skipped* si falta su programa externo.

---

## Solución de problemas

| Síntoma | Causa | Solución |
|---|---|---|
| OCR u Office aparecen en gris | Falta el programa externo | Ejecuta `install_vendor.bat` o `install_vendor.sh` y reinicia el servidor |
| `DLL load failed ... nombre demasiado largo` al importar pikepdf | La ruta del proyecto es demasiado larga para Windows | Usa una ruta corta (p. ej. `D:\pdf_local`) |
| "tiene contraseña: usa 'Desbloquear PDF' primero" | El PDF está cifrado | Pasa antes por *Desbloquear PDF* |
| OCR no reconoce texto en español | Faltan los datos de español | Vuelve a ejecutar el instalador (Windows) o instala `tesseract-lang` / `tesseract-ocr-spa` |
| `Permission denied` al ejecutar `.sh` | Falta permiso de ejecución | `chmod +x run.sh install_vendor.sh` |
| "Los archivos superan 500 MB" | Límite de subida | Sube menos archivos a la vez o cambia `MAX_UPLOAD_MB` en `app.py` |
| El puerto 5000 está ocupado | Otro programa lo usa | Cambia `PORT` en `app.py` |
