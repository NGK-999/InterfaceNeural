#!/bin/sh
set -eu
PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
if [ ! -x "$PROJECT_DIR/.venv/bin/python" ]; then
    echo 'Ambiente virtual ausente. Siga a instalação no README.md.' >&2
    exit 1
fi
exec "$PROJECT_DIR/.venv/bin/python" -m muscle_monitor "$@"

