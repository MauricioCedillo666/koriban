#!/usr/bin/env bash
# Koriban - arranque del prototipo (macOS / Linux)
set -e
cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ]; then
  echo "[1/5] Creando entorno virtual..."
  python3 -m venv .venv
fi
source .venv/bin/activate

echo "[2/5] Instalando dependencias..."
python -m pip install --quiet --disable-pip-version-check -r requirements.txt

echo "[3/5] Preparando base de datos..."
python manage.py makemigrations crm --noinput
python manage.py migrate --noinput

echo "[4/5] Cargando datos de demostración..."
python manage.py cargar_demo

echo "[5/5] Servidor en http://127.0.0.1:8000/  (Ctrl + C para detener)"
python manage.py runserver
