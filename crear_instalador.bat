@echo off
setlocal
cd /d "%~dp0"
call crear_exe.bat --sin-pausa
if errorlevel 1 goto error
REM Puede definir BIBLIOTECA_ISCC con la ruta completa de ISCC.exe.
if defined BIBLIOTECA_ISCC goto compilar
for %%D in ("%ProgramFiles%\Inno Setup 7" "%ProgramFiles(x86)%\Inno Setup 7" "%LOCALAPPDATA%\Programs\Inno Setup 7" "%ProgramFiles%\Inno Setup 6" "%ProgramFiles(x86)%\Inno Setup 6" "%LOCALAPPDATA%\Programs\Inno Setup 6") do if exist "%%~D\ISCC.exe" set "BIBLIOTECA_ISCC=%%~D\ISCC.exe"
if defined BIBLIOTECA_ISCC goto compilar
for /f "delims=" %%I in ('where ISCC.exe 2^>nul') do set "BIBLIOTECA_ISCC=%%I"
if not defined BIBLIOTECA_ISCC goto sin_inno
:compilar
"%BIBLIOTECA_ISCC%" instalador\BibliotecaEscolar360.iss
if errorlevel 1 goto error
echo.
echo LISTO: instalador creado en %CD%\instaladores
if /i not "%~1"=="--sin-pausa" pause
exit /b 0
:sin_inno
echo No se encontro Inno Setup. Abra instalador\BibliotecaEscolar360.iss
echo en Inno Setup Compiler y pulse Build - Compile para generar el instalador.
:error
echo ERROR: no se pudo completar el instalador. Revise el mensaje anterior.
if /i not "%~1"=="--sin-pausa" pause
exit /b 1
