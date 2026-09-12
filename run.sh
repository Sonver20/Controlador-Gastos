#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

unset GTK_PATH GTK_EXE_PREFIX GTK_IM_MODULE_FILE GTK_MODULES
unset GIO_MODULE_DIR GIO_LAUNCHED_DESKTOP_FILE

exec "$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/app.py"