# electron-builder falla extrayendo wincodesign por falta de privilegio para symlinks

**Error:** `ERROR: Cannot create symbolic link : El cliente no dispone de un privilegio requerido. : ...\electron-builder\Cache\winCodeSign\...\darwin\10.12\lib\libcrypto.dylib`

**Causa:** electron-builder descarga winCodeSign (rcedit/signtool) para firmar y editar el exe; el 7z contiene symlinks de macOS y Windows sin Modo Desarrollador/admin no permite crearlos.

**Solución implementada:** `electron/package.json` → `"win": { "signAndEditExecutable": false, ... }` (sin certificado no se firma; evita descargar winCodeSign). Alternativa: activar Modo Desarrollador de Windows.

**Resultado:** `npx electron-builder --win portable zip` empaqueta sin el paso de firma.

---
# ocr congelado con pyinstaller cuelga la petición (sys.executable -m ocrmypdf relanza el servidor)

**Error:** `POST /api/ocr` nunca responde en el exe empaquetado; aparecen 2 procesos `pdf_local_server.exe`.

**Causa:** `tools/external.py` ejecuta `[sys.executable, "-m", "ocrmypdf", ...]`; congelado, `sys.executable` = `pdf_local_server.exe`, que ignora los args y arranca otro Flask.

**Solución implementada:** `app.py` → `multiprocessing.freeze_support()` + `_run_frozen_module()`: si `sys.frozen` y `argv[1:3] == ["-m","ocrmypdf"]` → `ocrmypdf.__main__.run(argv[3:])`.

**Resultado:** el subproceso OCR corre ocrmypdf en vez de un segundo servidor.

---
# modulenotfounderror unittest en ocrmypdf dentro del backend pyinstaller

**Error:** `File "ocrmypdf\pdfinfo\layout.py", line 15 ... from unittest.mock import patch` → `ModuleNotFoundError: No module named 'unittest'`

**Causa:** `backend.spec` excluía `unittest` para reducir tamaño; ocrmypdf lo importa en tiempo de ejecución.

**Solución implementada:** `backend.spec` → `excludes=["pytest", "tkinter", "pydoc"]` (sin `unittest`); recompilar con `npm run build:py` en `electron/`.

**Resultado:** OCR funciona en el exe empaquetado.

---
# fuga de memoria del servidor por caché global de mupdf sin límite

**Error:** prueba de carga (13 herramientas × 5 rondas, PDF de 150 págs con imágenes): RSS 387 → 815 MB, crecimiento lineal ~110 MB/ronda. Herramientas afectadas: compress, pdf_to_img, pdf_to_word/excel/ppt, preview.

**Causa:** `pymupdf.TOOLS.store_maxsize()` = `None` (caché ilimitada); los recursos decodificados (imágenes, fuentes) quedan en la caché global tras cerrar el documento. `store_size()` reporta 0, así que no se ve desde Python.

**Solución implementada:**
- `core/pdf_io.py` → `release_cache()` = `pymupdf.TOOLS.store_shrink(100)`.
- `app.py` `process()` → `try/finally: release_cache()` tras cada herramienta.
- `tools/preview.py` `PreviewStore.add` → `release_cache()` al descartar documentos por LRU (no en cada miniatura, para conservar la caché entre páginas).

**Resultado:** en proceso: 509 MB → 220 MB y estable (218–222 MB) en iteraciones repetidas.

---
