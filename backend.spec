# PyInstaller: congela el servidor Flask para la app de escritorio.
# Uso: pyinstaller backend.spec --distpath electron/build --workpath electron/build/tmp --noconfirm
from PyInstaller.utils.hooks import collect_all

datas = [("static", "static")]
binaries = []
hiddenimports = []
# ocrmypdf carga sus plugins por entry points; pikepdf y pymupdf traen datos propios.
for package in ("ocrmypdf", "pikepdf", "pymupdf", "pdf2docx"):
    package_datas, package_binaries, package_imports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_imports

analysis = Analysis(
    ["app.py"],
    datas=datas,
    binaries=binaries,
    hiddenimports=hiddenimports,
    excludes=["pytest", "tkinter", "pydoc"],
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    exclude_binaries=True,
    name="pdf_local_server",
    console=False,
)
COLLECT(exe, analysis.binaries, analysis.datas, name="backend")
