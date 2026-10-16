@echo off
REM Compatibilidad con el nombre del script anterior.
call "%~dp0crear_exe.bat" %*
exit /b %errorlevel%
