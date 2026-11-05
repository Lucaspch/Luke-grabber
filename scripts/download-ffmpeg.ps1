# ==============================================================================
# Script de Download Automático do FFmpeg para Luke-Grabber
# Baixa e extrai ffmpeg.exe e ffprobe.exe diretamente para a pasta bin/
# ==============================================================================

$ErrorActionPreference = "Stop"
$rootDir = Split-Path -Parent $PSScriptRoot
$binDir = Join-Path $rootDir "bin"

if (-not (Test-Path $binDir)) {
    New-Item -ItemType Directory -Path $binDir | Out-Null
}

$ffmpegExe = Join-Path $binDir "ffmpeg.exe"
$ffprobeExe = Join-Path $binDir "ffprobe.exe"

if ((Test-Path $ffmpegExe) -and (Test-Path $ffprobeExe)) {
    Write-Host "[OK] FFmpeg e FFprobe já estão presentes em '$binDir'." -ForegroundColor Green
    exit 0
}

Write-Host "Baixando versão estática do FFmpeg para Windows..." -ForegroundColor Cyan
$zipUrl = "https://github.com/GyanD/codexffmpeg/releases/download/2024-10-28-git-3b47665dc7/ffmpeg-2024-10-28-git-3b47665dc7-essentials_build.zip"
$tempZip = Join-Path $env:TEMP "ffmpeg-temp.zip"

Invoke-WebRequest -Uri $zipUrl -OutFile $tempZip -UseBasicParsing
Write-Host "Extraindo binários para '$binDir'..." -ForegroundColor Cyan

$tempExtract = Join-Path $env:TEMP "ffmpeg-extract"
if (Test-Path $tempExtract) { Remove-Item $tempExtract -Recurse -Force }
Expand-Archive -Path $tempZip -DestinationPath $tempExtract -Force

$extractedBin = Get-ChildItem -Path $tempExtract -Recurse -Filter "ffmpeg.exe" | Select-Object -First 1
if ($extractedBin) {
    Copy-Item $extractedBin.FullName -Destination $binDir -Force
    $probeBin = Join-Path $extractedBin.DirectoryName "ffprobe.exe"
    if (Test-Path $probeBin) {
        Copy-Item $probeBin -Destination $binDir -Force
    }
}

Remove-Item $tempZip -Force -ErrorAction SilentlyContinue
Remove-Item $tempExtract -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "[Sucesso] FFmpeg configurado em '$binDir'!" -ForegroundColor Green
