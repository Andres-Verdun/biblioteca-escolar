@echo off
setlocal
cd /d "%~dp0"
echo BIBLIOTECA ESCOLAR 360 - GENERAR EJECUTABLE WINDOWS X64
if not defined LOCALAPPDATA set "LOCALAPPDATA=%USERPROFILE%\AppData\Local"
set "BIBLIOTECA_PYTHON=%LOCALAPPDATA%\BibliotecaEscolar360\venv-build-312\Scripts\python.exe"
if exist "%BIBLIOTECA_PYTHON%" goto preparar
where py >nul 2>nul
if errorlevel 1 goto sin_python
py -3.12 -m venv "%LOCALAPPDATA%\BibliotecaEscolar360\venv-build-312"
if errorlevel 1 goto sin_python
:preparar
"%BIBLIOTECA_PYTHON%" -c "import struct,sys; sys.exit(0 if struct.calcsize('P') == 8 and sys.version_info[:2] == (3,12) else 1)"
if errorlevel 1 goto sin_python
"%BIBLIOTECA_PYTHON%" -m pip install -r requirements-build.txt
if errorlevel 1 goto error
"%BIBLIOTECA_PYTHON%" -m PyInstaller --noconfirm --clean BibliotecaEscolar.spec
if errorlevel 1 goto error
if not exist "dist\BibliotecaEscolar.exe" goto error
echo.
echo LISTO: %CD%\dist\BibliotecaEscolar.exe
if /i not "%~1"=="--sin-pausa" pause
exit /b 0
:sin_python
echo Se necesita Python 3.12 de 64 bits con el lanzador py.
echo Instale Python 3.12 desde python.org y vuelva a ejecutar este archivo.
echo Si el entorno de compilacion falla, borre la carpeta venv-build-312 en AppData.
goto error
:error
echo ERROR: no se pudo crear el ejecutable. Revise el mensaje anterior.
if /i not "%~1"=="--sin-pausa" pause
exit /b 1
