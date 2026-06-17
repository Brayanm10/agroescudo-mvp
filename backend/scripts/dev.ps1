$ErrorActionPreference = "Stop"

$backendRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $backendRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "No se encontro backend\.venv. Crea el entorno virtual e instala requirements.txt."
}

Set-Location $backendRoot
& $python -m uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload
