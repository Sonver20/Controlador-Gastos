#!/bin/bash
# Launcher automatico do Controlador de Gastos
# Usa o Python do venv diretamente (evita conflito com snap)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
"$SCRIPT_DIR/.venv/bin/python3" app.py
