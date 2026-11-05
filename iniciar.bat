@echo off
title Luke-Grabber — Extrator Multimidia Universal
cd /d "%~dp0"

:: Inicia o aplicativo standalone
echo ========================================================
echo   INICIANDO LUKE-GRABBER (EXTRATOR MULTIMIDIA UNIVERSAL)
echo   Motor Local: yt-dlp + FFmpeg (100%% Seguro e Standalone)
echo ========================================================

python app.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Ocorreu um erro ao iniciar. Verifique se o Python esta instalado.
    pause
)
