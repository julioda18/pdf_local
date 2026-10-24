# Copia ..\vendor a build\vendor sin lo que la app no usa (docs, galerías, entrenamiento).
# El vendor original no se toca.
$ErrorActionPreference = "Stop"
$source = Join-Path $PSScriptRoot "..\vendor"
$target = Join-Path $PSScriptRoot "build\vendor"

if (-not (Test-Path $source)) { throw "Falta vendor/. Ejecuta: python scripts/install_vendor.py" }

$excludeDirs = @(
    "doc", "help", "gallery", "template", "wizards", "readmes",
    (Join-Path $source "LibreOffice\share\extensions")
)
$excludeFiles = @("*.jar", "*.html", "*training*.exe", "*.user-*", "unins*.exe", "*uninstall*.exe")

robocopy $source $target /MIR /NFL /NDL /NJH /NP /XD $excludeDirs /XF $excludeFiles
# robocopy: códigos < 8 son éxito.
if ($LASTEXITCODE -ge 8) { throw "robocopy falló ($LASTEXITCODE)" }
$global:LASTEXITCODE = 0
