@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo   BIBLIOTECA ESCOLAR 360 - GENERAR EJECUTABLE
echo ============================================================
echo.
echo Carpeta del proyecto:
echo %CD%
echo.

REM Python dentro de la venv local del proyecto
set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"

REM Si la venv no existe, crearla
if not exist "%PYTHON_EXE%" (
    echo No se encontro .venv\Scripts\python.exe
    echo Creando una venv nueva en .venv...
    echo.
    py -m venv .venv
    if errorlevel 1 (
        echo.
        echo ERROR: no se pudo crear la venv con el comando py.
        echo Proba ejecutar: python -m venv .venv
        echo.
        pause
        exit /b 1
    )
)

REM Volver a comprobar la ruta
if not exist "%PYTHON_EXE%" (
    echo.
    echo ERROR: sigue sin existir:
    echo %PYTHON_EXE%
    echo.
    pause
    exit /b 1
)

echo Python que se va a usar:
echo %PYTHON_EXE%
echo.

if not exist "cdd_bnm.csv" (
    echo ERROR: falta cdd_bnm.csv junto al proyecto.
    pause
    exit /b 1
)

if not exist "main.py" (
    echo ERROR: no se encontro main.py en:
    echo %CD%
    echo.
    pause
    exit /b 1
)

echo [1/3] Instalando o actualizando PyInstaller...
"%PYTHON_EXE%" -m pip install --upgrade pyinstaller
if errorlevel 1 goto :error

echo.
echo [2/3] Instalando reportlab y pillow...
"%PYTHON_EXE%" -m pip install --upgrade reportlab pillow
if errorlevel 1 goto :error

echo.
echo [3/3] Generando BibliotecaEscolar.exe...
"%PYTHON_EXE%" -m PyInstaller --noconfirm --clean BibliotecaEscolar.spec
if errorlevel 1 goto :error

if not exist "dist\BibliotecaEscolar.exe" (
    echo.
    echo ERROR: PyInstaller termino, pero no aparece dist\BibliotecaEscolar.exe
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   LISTO
echo   Ejecutable creado correctamente en:
echo   %CD%\dist\BibliotecaEscolar.exe
echo ============================================================
echo.
pause
exit /b 0

:error
echo.
echo ============================================================
echo   ERROR: el proceso se detuvo.
echo   Lee el mensaje que aparece arriba para ver la causa.
echo ============================================================
echo.
pause
exit /b 1
