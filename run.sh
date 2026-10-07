#!/bin/sh
cd "$(dirname "$0")" || exit 1
exec "${PYTHON_EXE:-python3}" -m src "$@"
