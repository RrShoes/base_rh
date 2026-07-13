@echo off
chcp 65001 > nul
title Desinstalar Serviço: Base RH

echo ============================================
echo   Desinstalador do Serviço Windows - Base RH
echo ============================================
echo.

cd /d "%~dp0"

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERRO] Este script precisa ser executado como ADMINISTRADOR.
    echo Por favor, clique com o botão direito e escolha "Executar como Administrador".
    echo.
    pause
    exit /b 1
)

echo [1/2] Parando o serviço BaseRhService...
sc stop BaseRhService >nul 2>&1
timeout /t 2 >nul

echo [2/2] Removendo o serviço do Windows...
sc delete BaseRhService
if %errorLevel% neq 0 (
    echo [AVISO] Falha ou o serviço não estava registrado.
) else (
    echo [OK] Serviço removido com sucesso.
)

if exist BaseRhService.exe (
    del /f /q BaseRhService.exe >nul 2>&1
    echo [OK] BaseRhService.exe removido.
)
if exist BaseRhService.pdb (
    del /f /q BaseRhService.pdb >nul 2>&1
)

echo.
echo ============================================
echo   Desinstalação concluída.
echo ============================================
echo.
pause
