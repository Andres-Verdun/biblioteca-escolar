# Solo para el entorno descartable de GitHub Actions; no ejecutar con datos reales.
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Esta prueba solo puede ejecutarse en GitHub Actions.' }
$instalador = (Get-ChildItem instaladores/*-x64.exe | Select-Object -First 1).FullName
$directorio = Join-Path $env:LOCALAPPDATA 'Programs\BibliotecaEscolar360'
$datos = Join-Path $env:LOCALAPPDATA 'BibliotecaEscolar360\biblioteca.db'
if (Test-Path $datos) { throw 'Ya hay datos; no se ejecutara la prueba.' }
function Ejecutar($archivo, $argumentos) {
    $proceso = Start-Process -FilePath $archivo -ArgumentList $argumentos -Wait -PassThru
    if ($proceso.ExitCode -ne 0) { throw "Fallo $archivo, codigo $($proceso.ExitCode)" }
}
Ejecutar $instalador '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-'
$programa = Join-Path $directorio 'BibliotecaEscolar.exe'
Ejecutar $programa '--comprobar-instalacion'
if (!(Test-Path $datos)) { throw 'No se creo la base fuera de la carpeta del programa.' }
python -c "import sqlite3,os; p=os.path.join(os.environ['LOCALAPPDATA'],'BibliotecaEscolar360','biblioteca.db'); c=sqlite3.connect(p); assert c.execute('SELECT count(*) FROM cdd_bnm').fetchone()[0] >= 275; c.execute('CREATE TABLE prueba_actualizacion (valor TEXT)'); c.execute('INSERT INTO prueba_actualizacion VALUES (?)',('conservar',)); c.commit(); c.close()"
if ($LASTEXITCODE -ne 0) { throw 'Fallo la preparacion de datos' }
Ejecutar $instalador '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-'
Ejecutar $programa '--comprobar-instalacion'
Ejecutar (Join-Path $directorio 'unins000.exe') '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART'
python -c "import sqlite3,os; p=os.path.join(os.environ['LOCALAPPDATA'],'BibliotecaEscolar360','biblioteca.db'); assert os.path.isfile(p); c=sqlite3.connect(p); assert c.execute('SELECT valor FROM prueba_actualizacion').fetchone()[0]=='conservar'; c.close()"
if ($LASTEXITCODE -ne 0) { throw 'No se conservaron los datos' }
if (Test-Path $programa) { throw 'No se desinstalo el ejecutable' }
