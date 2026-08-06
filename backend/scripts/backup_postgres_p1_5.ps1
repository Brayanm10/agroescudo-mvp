param(
  [string]$OutputDirectory = "..\..\var\backups"
)

$ErrorActionPreference = "Stop"
if (-not $env:DATABASE_URL) {
  throw "DATABASE_URL no configurada. No se puede respaldar PostgreSQL."
}
if ($env:DATABASE_URL -notmatch "^postgres") {
  throw "Este script exige una URL PostgreSQL."
}
$pgDump = Get-Command pg_dump -ErrorAction SilentlyContinue
if (-not $pgDump) {
  throw "pg_dump no esta instalado o no esta disponible en PATH."
}

$resolved = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot $OutputDirectory))
New-Item -ItemType Directory -Force -Path $resolved | Out-Null
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$target = Join-Path $resolved "agroescudo_pre_p1_5_$stamp.dump"
$dumpUrl = $env:DATABASE_URL -replace "^postgresql\+psycopg://", "postgresql://"
& $pgDump.Source --format=custom --no-owner --no-acl --file=$target $dumpUrl
if ($LASTEXITCODE -ne 0) {
  throw "pg_dump fallo con codigo $LASTEXITCODE."
}
$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $target).Hash.ToLowerInvariant()
Write-Output "BACKUP=$target"
Write-Output "SHA256=$hash"
Write-Output "SIZE_BYTES=$((Get-Item -LiteralPath $target).Length)"
