$ErrorActionPreference = "Stop"

$backendRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $backendRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "No se encontro backend\.venv. Crea el entorno virtual e instala requirements.txt."
}

Set-Location $backendRoot
& $python -m pytest -p no:cacheprovider
