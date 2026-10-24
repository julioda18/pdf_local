"""Prepara PDF Local de cero: entorno virtual de Python y programas externos.

Uso:
    python scripts/install_vendor.py

1. Crea ``.venv`` (si no existe) e instala ``requirements.txt`` en él.
2. Instala Tesseract (+ español), Ghostscript y LibreOffice:

- Windows: todo queda dentro de ``vendor/`` del proyecto (nada en C:\\Program Files).
- macOS: Homebrew (``brew``); los programas quedan en las rutas de Homebrew.
- Linux: apt, dnf, pacman o zypper con ``sudo``; quedan en las rutas del sistema.

Es idempotente: lo que ya está instalado se omite. Solo usa la biblioteca estándar,
así que puede ejecutarse antes de crear el ``.venv``.
"""

import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
VENDOR_DIR = PROJECT_DIR / "vendor"
VENV_DIR = PROJECT_DIR / ".venv"
REQUIREMENTS_FILE = PROJECT_DIR / "requirements.txt"
sys.path.insert(0, str(PROJECT_DIR))

from core.binaries import find_binary  # noqa: E402

PROGRAMS = ("tesseract", "ghostscript", "libreoffice")
SPANISH_TRAINEDDATA_URL = "https://github.com/tesseract-ocr/tessdata_fast/raw/main/spa.traineddata"
GHOSTSCRIPT_RELEASES_API = "https://api.github.com/repos/ArtifexSoftware/ghostpdl-downloads/releases/latest"
WINGET_FLAGS = ["-e", "--silent", "--accept-package-agreements", "--accept-source-agreements"]
TESSERACT_PROGRAM_FILES = Path(r"C:\Program Files\Tesseract-OCR")

BREW_FORMULAS = {"tesseract": ["tesseract", "tesseract-lang"], "ghostscript": ["ghostscript"]}
BREW_CASKS = {"libreoffice": ["libreoffice"]}
# Paquetes por gestor de Linux; en todos, Tesseract incluye el idioma español aparte.
LINUX_PACKAGES = {
    "apt-get": {"tesseract": ["tesseract-ocr", "tesseract-ocr-spa"], "ghostscript": ["ghostscript"],
                "libreoffice": ["libreoffice-core", "libreoffice-writer", "libreoffice-calc", "libreoffice-impress"]},
    "dnf": {"tesseract": ["tesseract", "tesseract-langpack-spa"], "ghostscript": ["ghostscript"],
            "libreoffice": ["libreoffice-core", "libreoffice-writer", "libreoffice-calc", "libreoffice-impress"]},
    "pacman": {"tesseract": ["tesseract", "tesseract-data-spa"], "ghostscript": ["ghostscript"],
               "libreoffice": ["libreoffice-fresh"]},
    "zypper": {"tesseract": ["tesseract-ocr", "tesseract-ocr-traineddata-spanish"], "ghostscript": ["ghostscript"],
               "libreoffice": ["libreoffice-writer", "libreoffice-calc", "libreoffice-impress"]},
}
LINUX_INSTALL_ARGS = {
    "apt-get": ["install", "-y"], "dnf": ["install", "-y"],
    "pacman": ["-S", "--noconfirm", "--needed"], "zypper": ["--non-interactive", "install"],
}


def log(message):
    print(f"[vendor] {message}", flush=True)


def run(args):
    """Ejecuta un comando mostrando su salida; aborta si falla."""
    log("$ " + " ".join(map(str, args)))
    subprocess.run(list(map(str, args)), check=True)


def download(url, target):
    """Descarga ``url`` en ``target`` y devuelve la ruta."""
    log(f"Descargando {url}")
    target.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, target)
    return target


def missing_programs():
    """Programas de ``PROGRAMS`` que todavía no se encuentran."""
    find_binary.cache_clear()
    return [name for name in PROGRAMS if find_binary(name) is None]


# --- Windows ---------------------------------------------------------------

def run_elevated(executable, *args):
    """Ejecuta como administrador (UAC) y espera a que termine."""
    arg_list = ",".join(f"'{a}'" for a in args)
    run(["powershell", "-NoProfile", "-Command",
         f"Start-Process -FilePath '{executable}' -ArgumentList {arg_list} -Verb RunAs -Wait"])


def install_libreoffice_windows():
    run(["winget", "install", "--id", "TheDocumentFoundation.LibreOffice", *WINGET_FLAGS,
         "--location", VENDOR_DIR / "LibreOffice"])


def install_ghostscript_windows():
    with urllib.request.urlopen(GHOSTSCRIPT_RELEASES_API) as response:
        assets = json.load(response)["assets"]
    url = next(a["browser_download_url"] for a in assets if a["name"].endswith("w64.exe"))
    with tempfile.TemporaryDirectory() as folder:
        installer = download(url, Path(folder) / "gs_setup.exe")
        # NSIS exige que /D= sea el último argumento y sin comillas.
        run_elevated(installer, "/S", f"/D={VENDOR_DIR / 'gs'}")


def install_tesseract_windows():
    """Instala en Program Files, copia a vendor/ y desinstala la copia del sistema.

    El instalador de Tesseract ignora /D= y la opción --location de winget, pero el
    programa es portable, así que se reubica copiando la carpeta.
    """
    with tempfile.TemporaryDirectory() as folder:
        run(["winget", "download", "--id", "UB-Mannheim.TesseractOCR", "-d", folder, *WINGET_FLAGS[2:]])
        run_elevated(next(Path(folder).glob("*.exe")), "/S")
    shutil.copytree(TESSERACT_PROGRAM_FILES, VENDOR_DIR / "Tesseract-OCR", dirs_exist_ok=True)
    run_elevated(TESSERACT_PROGRAM_FILES / "tesseract-uninstall.exe", "/S")


def ensure_spanish_traineddata_windows():
    """Los datos de español no vienen con el instalador de Windows."""
    target = VENDOR_DIR / "Tesseract-OCR" / "tessdata" / "spa.traineddata"
    if target.parent.exists() and not target.exists():
        download(SPANISH_TRAINEDDATA_URL, target)


WINDOWS_INSTALLERS = {
    "tesseract": install_tesseract_windows,
    "ghostscript": install_ghostscript_windows,
    "libreoffice": install_libreoffice_windows,
}


def install_windows(missing):
    if not shutil.which("winget"):
        sys.exit("winget no está disponible. Instala 'App Installer' desde Microsoft Store.")
    VENDOR_DIR.mkdir(exist_ok=True)
    for name in missing:
        WINDOWS_INSTALLERS[name]()
    ensure_spanish_traineddata_windows()


# --- macOS -----------------------------------------------------------------

def install_macos(missing):
    if not shutil.which("brew"):
        sys.exit("Homebrew no está instalado: https://brew.sh")
    formulas = [pkg for name in missing for pkg in BREW_FORMULAS.get(name, [])]
    casks = [pkg for name in missing for pkg in BREW_CASKS.get(name, [])]
    if formulas:
        run(["brew", "install", *formulas])
    if casks:
        run(["brew", "install", "--cask", *casks])


# --- Linux -----------------------------------------------------------------

def install_linux(missing):
    manager = next((m for m in LINUX_PACKAGES if shutil.which(m)), None)
    if manager is None:
        sys.exit(f"Gestor de paquetes no soportado. Instala a mano: {', '.join(missing)}")
    packages = [pkg for name in missing for pkg in LINUX_PACKAGES[manager][name]]
    sudo = [] if _is_root() else ["sudo"]
    if manager == "apt-get":
        run([*sudo, "apt-get", "update"])
    run([*sudo, manager, *LINUX_INSTALL_ARGS[manager], *packages])


def _is_root():
    return hasattr(os, "geteuid") and os.geteuid() == 0


# --- Entorno virtual -------------------------------------------------------

def venv_python():
    """Ruta del intérprete de ``.venv`` (``Scripts`` en Windows, ``bin`` en el resto)."""
    folder, executable = ("Scripts", "python.exe") if platform.system() == "Windows" else ("bin", "python")
    return VENV_DIR / folder / executable


def ensure_venv():
    """Crea ``.venv`` si falta e instala o actualiza ``requirements.txt``.

    pip se ejecuta siempre: si todo está al día termina en segundos, y así un
    ``requirements.txt`` modificado se aplica al volver a lanzar el instalador.
    """
    if not venv_python().exists():
        log(f"Creando entorno virtual en {VENV_DIR}")
        run([sys.executable, "-m", "venv", VENV_DIR])
    run([venv_python(), "-m", "pip", "install", "--disable-pip-version-check", "-q", "-r", REQUIREMENTS_FILE])


# --- Main ------------------------------------------------------------------

INSTALLERS_BY_OS = {"Windows": install_windows, "Darwin": install_macos, "Linux": install_linux}


def install_external_programs(system):
    """Instala los programas que falten con el instalador propio de ``system``."""
    installer = INSTALLERS_BY_OS.get(system) or sys.exit(f"Sistema no soportado: {system}")
    missing = missing_programs()
    if missing:
        log(f"Sistema: {system}. Faltan: {', '.join(missing)}")
        installer(missing)
    elif system == "Windows":
        ensure_spanish_traineddata_windows()


def report():
    """Muestra dónde quedó cada componente y devuelve ``True`` si no falta ninguno."""
    log(f"{'venv':12} -> {venv_python()}")
    for name in PROGRAMS:
        log(f"{name:12} -> {find_binary(name) or 'NO ENCONTRADO'}")
    return not missing_programs()


def main():
    ensure_venv()
    install_external_programs(platform.system())
    sys.exit(0 if report() else 1)


if __name__ == "__main__":
    main()
