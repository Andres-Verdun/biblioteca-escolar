@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
if errorlevel 1 goto :error

set "CARPETA_PROYECTO=%CD%"
if not defined LOCALAPPDATA set "LOCALAPPDATA=%USERPROFILE%\AppData\Local"
set "ENTORNO=%LOCALAPPDATA%\BibliotecaEscolar360\venv-compilacion"
set "PYTHON_EXE=%ENTORNO%\Scripts\python.exe"

echo ============================================================
echo   BIBLIOTECA ESCOLAR 360 - GENERAR EJECUTABLE
echo ============================================================
echo.
echo Proyecto: %CARPETA_PROYECTO%
echo Entorno Python permanente: %ENTORNO%
echo.

REM Comprobar recursos ANTES de instalar o usar Python.
if not exist "main.py" (
    echo ERROR: falta main.py en la carpeta del proyecto.
    goto :error
)
if not exist "BibliotecaEscolar.spec" (
    echo ERROR: falta BibliotecaEscolar.spec en la carpeta del proyecto.
    goto :error
)
if not exist "cdd_bnm.csv" (
    echo ERROR: falta cdd_bnm.csv en la carpeta del proyecto.
    goto :error
)

REM El entorno se guarda FUERA de la carpeta descargada, para reutilizarlo.
REM Si Python fue desinstalado o cambiado, reconstruir el entorno dañado.
if exist "%PYTHON_EXE%" (
    "%PYTHON_EXE%" -c "import sys" >nul 2>&1
    if errorlevel 1 (
        echo El entorno anterior ya no funciona. Se va a reconstruir.
        rmdir /s /q "%ENTORNO%" 2>nul
    )
)

if not exist "%PYTHON_EXE%" (
    echo [1/3] Preparando entorno Python por unica vez en este equipo...
    set "PY_LAUNCHER="
    py -3 -c "import sys" >nul 2>&1
    if not errorlevel 1 set "PY_LAUNCHER=py -3"
    if not defined PY_LAUNCHER (
        python -c "import sys" >nul 2>&1
        if not errorlevel 1 set "PY_LAUNCHER=python"
    )
    if not defined PY_LAUNCHER (
        echo ERROR: no se encontro Python 3 instalado en Windows.
        echo Instala Python 3 desde python.org y vuelve a intentar.
        goto :error
    )
    !PY_LAUNCHER! -m venv "%ENTORNO%"
    if errorlevel 1 goto :error
) else (
    echo [1/3] Reutilizando el entorno Python permanente.
)

if not exist "%PYTHON_EXE%" (
    echo ERROR: no se pudo crear o recuperar el entorno Python.
    goto :error
)

echo.
echo [2/3] Comprobando dependencias...
"%PYTHON_EXE%" -m pip --version >nul 2>&1
if errorlevel 1 (
    "%PYTHON_EXE%" -m ensurepip --upgrade
    if errorlevel 1 goto :error
)
"%PYTHON_EXE%" -c "import PyInstaller, reportlab, PIL" >nul 2>&1
if errorlevel 1 (
    echo Faltan dependencias. Se instalaran solo las necesarias...
    "%PYTHON_EXE%" -m pip install pyinstaller reportlab pillow
    if errorlevel 1 goto :error
) else (
    echo PyInstaller, ReportLab y Pillow ya estan disponibles.
)

echo.
echo [3/3] Generando BibliotecaEscolar.exe...
"%PYTHON_EXE%" -m PyInstaller --noconfirm "BibliotecaEscolar.spec"
if errorlevel 1 goto :error

if not exist "dist\BibliotecaEscolar.exe" (
    echo ERROR: PyInstaller termino, pero no aparece dist\BibliotecaEscolar.exe.
    goto :error
)

echo.
echo ============================================================
echo   LISTO: Ejecutable generado correctamente.
echo   %CARPETA_PROYECTO%\dist\BibliotecaEscolar.exe
echo ============================================================
echo.
echo El ejecutable generado NO necesita un entorno virtual.
pause
exit /b 0

:error
echo.
echo ============================================================
echo   ERROR: no se pudo generar el ejecutable.
echo   Revisa el mensaje anterior.
echo ============================================================
echo.
pause
exit /b 1
