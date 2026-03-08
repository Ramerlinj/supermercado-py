#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_GUNICORN="$PROJECT_DIR/.venv/bin/gunicorn"

if [ ! -x "$VENV_GUNICORN" ]; then
	echo "No se encontro $VENV_GUNICORN"
	echo "Activa el entorno e instala dependencias:"
	echo "  source .venv/bin/activate && pip install -r requirements.txt"
	exit 1
fi

exec "$VENV_GUNICORN" index:app