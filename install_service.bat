@echo off
chcp 65001 > nul
title Instalar Serviço: Base RH

echo ============================================
echo   Instalador do Serviço Windows - Base RH
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

set CSC_PATH=C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe
if not exist "%CSC_PATH%" (
    set CSC_PATH=C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe
)

if not exist "%CSC_PATH%" (
    echo [ERRO] Compilador C# (csc.exe) não encontrado no sistema.
    pause
    exit /b 1
)

echo [1/3] Compilando o serviço C#...
"%CSC_PATH%" /reference:System.ServiceProcess.dll /out:BaseRhService.exe BaseRhService.cs
if %errorLevel% neq 0 (
    echo [ERRO] Falha na compilação do BaseRhService.cs.
    pause
    exit /b 1
)
echo [OK] Compilado com sucesso: BaseRhService.exe
echo.

echo [2/3] Removendo serviço anterior se existir...
sc stop BaseRhService >nul 2>&1
sc delete BaseRhService >nul 2>&1
timeout /t 2 >nul

echo [3/3] Registrando o novo serviço...
sc create BaseRhService binPath= "%~dp0BaseRhService.exe" start= delayed-auto displayName= "Base RH"
if %errorLevel% neq 0 (
    echo [ERRO] Falha ao criar o serviço Windows.
    pause
    exit /b 1
)

sc description BaseRhService "Roda a aplicação Flask do Base RH em background na porta 5062." >nul
echo [OK] Serviço registrado com sucesso!
echo.
echo ============================================
echo   Para iniciar o serviço, execute:
echo   net start BaseRhService
echo ============================================
echo.
pause
