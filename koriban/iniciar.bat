@echo off
chcp 65001 >nul
title Koriban - prototipo
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo No se encontro Python. Instala Python 3.10 o superior desde https://www.python.org
  echo y marca la casilla "Add Python to PATH" durante la instalacion.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/5] Creando entorno virtual...
  python -m venv .venv
)
call ".venv\Scripts\activate.bat"

echo [2/5] Instalando dependencias...
python -m pip install --quiet --disable-pip-version-check -r requirements.txt
if errorlevel 1 ( echo Error al instalar dependencias. & pause & exit /b 1 )

echo [3/5] Preparando base de datos...
python manage.py makemigrations crm --noinput
python manage.py migrate --noinput
if errorlevel 1 ( echo Error al crear la base de datos. & pause & exit /b 1 )

echo [4/5] Cargando datos de demostracion...
python manage.py cargar_demo

echo [5/5] Iniciando servidor en http://127.0.0.1:8000/
echo Para detenerlo presiona Ctrl + C
start "" cmd /c "timeout /t 4 >nul & start http://127.0.0.1:8000/"
python manage.py runserver
pause
