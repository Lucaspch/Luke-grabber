# ==============================================================================
# Script: Compilar Instalador e Versão Portátil do Luke-Grabber
# ==============================================================================

$ErrorActionPreference = "Stop"

$rootDir = Split-Path -Parent $PSScriptRoot
Set-Location $rootDir

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "         COMPILADOR DE INSTALADOR DO LUKE-GRABBER         " -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Limpeza de builds anteriores
Write-Host "`n[1/4] Limpando pastas de build anteriores..." -ForegroundColor White
if (Test-Path "build") { Remove-Item "build" -Recurse -Force -ErrorAction SilentlyContinue }
if (Test-Path "dist") { Remove-Item "dist" -Recurse -Force -ErrorAction SilentlyContinue }
if (-not (Test-Path "release")) { New-Item -ItemType Directory -Path "release" | Out-Null }

# 2. Compilação com PyInstaller
Write-Host "`n[2/4] Compilando executável com PyInstaller..." -ForegroundColor White
pyinstaller luke-grabber.spec --noconfirm

if (-not (Test-Path "dist\Luke-Grabber\Luke-Grabber.exe")) {
    Write-Error "Falha ao compilar Luke-Grabber.exe com PyInstaller."
    exit 1
}
Write-Host "  -> Binário standalone compilado em 'dist\Luke-Grabber'." -ForegroundColor Green

# 3. Gerando Pacote Portátil (.ZIP)
Write-Host "`n[3/4] Gerando pacote portátil (.zip)..." -ForegroundColor White
$zipPath = "release\Luke-Grabber_v1.1.1_Portable.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path "dist\Luke-Grabber\*" -DestinationPath $zipPath -CompressionLevel Optimal
$zipSizeMB = [math]::Round((Get-Item $zipPath).Length / 1MB, 2)
Write-Host "  -> Pacote Portátil gerado: $zipPath ($zipSizeMB MB)" -ForegroundColor Green

# 4. Compilação do Instalador com Inno Setup
Write-Host "`n[4/4] Gerando instalador Setup com Inno Setup..." -ForegroundColor White
$isccCandidates = @(
    "C:\Users\lucas\AppData\Local\Programs\Inno Setup 6\ISCC.exe",
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe"
)

$isccPath = $null
foreach ($path in $isccCandidates) {
    if (Test-Path $path) {
        $isccPath = $path
        break
    }
}

if ($isccPath) {
    & "$isccPath" "luke-grabber.iss"
    $setupExe = "release\Luke-Grabber_Setup_v1.1.1.exe"
    if (Test-Path $setupExe) {
        $setupSizeMB = [math]::Round((Get-Item $setupExe).Length / 1MB, 2)
        Write-Host "  -> Instalador gerado com sucesso: $setupExe ($setupSizeMB MB)" -ForegroundColor Green
    }
} else {
    Write-Warning "Compilador ISCC.exe do Inno Setup não encontrado. O pacote portátil .ZIP foi gerado com sucesso."
}

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host "            PACOTES PRONTOS PARA DISTRIBUIÇÃO!            " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan
Get-ChildItem "release" | Select-Object Name, @{Name="Tamanho (MB)"; Expression={[math]::Round($_.Length / 1MB, 2)}} | Format-Table -AutoSize
